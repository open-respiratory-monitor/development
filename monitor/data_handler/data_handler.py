#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May  3 16:43:51 2020

Data Handler

This file defines two loops which are started in the mainwindow

Fast Loop: update data
    - P1
    - P2
    - Flow
    - Volume
    - Pi GPIO State

Slow Loop: update calculations
    - Volume calibration (spline fit)
    - Breath parameters


@author: nlourie
"""

from PyQt5 import uic, QtCore, QtGui, QtWidgets
#from PyQt5.QtWidgets import QMessageBox

import numpy as np


#import time
#import traceback
#import signal
#import board
#import busio
#import adafruit_lps35hw
import os
import sys
from datetime import datetime
from scipy import interpolate
from scipy import signal
from scipy import integrate

try:
    import RPi.GPIO as GPIO
except Exception as e:
    print("Could not load Raspberry Pi GPIO module: ",e)

# add the wsp directory to the PATH
main_path = os.path.dirname(os.getcwd())
sys.path.insert(1, main_path)

# import custom modules
from sensor import sensor
from utils import utils


def beep():
    os.system('afplay /System/Library/Sounds/Sosumi.aiff')

"""
# Define the fast and slow data objects that will be passed to the GUI thread
"""
class fast_data(object):
    def __init__(self):

        # pressures
        self.p1 = np.array([])
        self.p2 = np.array([])
        self.dp = np.array([])

        # flow
        self.flow = np.array([])
        self.flow_raw = np.array([])
        self.dflow = np.array([])
        self.insp = np.array([])
        
        # volume
        self.vol_raw = np.array([])
        self.vol_drift = np.array([]) # the drift volume which is the spline line through the detrended volume
        self.vol = np.array([])
        
        # time
        self.t_obj = np.array([]) # datetime object
        self.dt = np.array([])    # dt since first sample in vector
        self.t = np.array([])     # ctime in seconds
        self.fs = []

        # all_fields (this is how the data filler wants data)
        self.all_fields = dict()

class breath_data(object):
    # vectors that just hold the last full breath of data
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.p = np.array([])
        self.flow = np.array([])
        self.vol = np.array([])
        self.dt = np.array([])
        self.tsi = float() # time of start of inspriation
        self.tei = float() # time of end of inspriation
        self.tee = float() # time of end of expriration




class slow_data(object):
    def __init__(self):


        self.t_last = datetime.utcnow().timestamp()
        self.dt_last = 0.0
        
        # pi GPIO state
        self.lowbatt = None
        self.charging = None

    def print_data(self):
        print('Parameters Checked Regularly by Slow Loop:')
        print(f'Time Since Last Detected Breath (s) = {self.dt_last}')
        print('Device Parameters:')
        print(f'Plugged In = {self.charging}')
        print(f'Low Battery = {self.lowbatt}')

class breath_par(object):
    # holds breath parameters as calculated from breath data
    
    def __init__(self):
        ## THINGS THAT HOLD SINGLE VALUES ##
        # respiratory parameters from last breath
        self.pip = None
        self.peep = None
        self.pp = None
        self.vt = None
        self.mve_inf = None
        self.mve_meas = None
        self.rr = None
        self.ie = None
        self.c = None
        
    def print_data(self):
        print('Respiratory Parameters:')
        print(f'PIP = {self.pip}')
        print(f'PEEP = {self.peep}')
        print(f'PP = {self.pp}')
        print(f'VT = {self.vt}')
        print(f'MVE Inferred = {self.mve_inf}')
        print(f'MVE Measured = {self.mve_meas}')
        print(f'RR = {self.rr}')
        print(f'I:E = {self.ie}')
        print(f'C = {self.c}')
        print()
    
def add_new_point(arr,new_point,maxlen):
       # adds a new data point to the array,
       # and keeps gets rid of the oldest point

       if len(arr) < maxlen:
           arr = np.append(arr,new_point)
       else:
           arr[:-1] = arr[1:]
           arr[-1] = new_point

       return arr




"""
# Define the fast and slow loops
"""
class fast_loop(QtCore.QThread):

    """
    This class gets and updates the data that gets plotted in realtime

    Needs to take a few things to get started:

        sensor -- an instance of the sensor class

    """
    # define a new signal that will be used to send updated data back to the main thread
    # this signal returns an object that holds the data to ship out to main
    newdata = QtCore.pyqtSignal(object)
    new_inhale = QtCore.pyqtSignal()
    new_exhale = QtCore.pyqtSignal()
    
    new_breath = QtCore.pyqtSignal(object) 

    def __init__(self, main_path, config, correct_vol = False, simulation = False,logdata = False,verbose = False):

        QtCore.QThread.__init__(self)

        # save a continuous log of the pressure data?
        self.logdata = logdata

        # run in simulation mode?
        self.simulation = simulation

        # run in verbose mode?
        self.verbose = verbose

        # get the main path
        self.main_path = main_path
        if self.verbose:
            print(f"fastloop: main path = {self.main_path}")

        #self.data_filler = data_filler
        self.config = config

        # Define the instance of the object that will hold all the data
        self.fastdata = fast_data()
        self.slowdata = slow_data()
        self.breathdata = breath_data()
        
        
        # current time loop is executed
        self.t_obj = datetime.utcnow()
        self.t = self.t_obj.timestamp()

        # time to display is the approx time to show on the screen in seconds
        self.time_to_display = self.config['display_time'] #s

        # time between samples
        self.ts = self.config['fastdata_interval'] #ms

        # real sample rate
        self.ts_real = []

        # sample frequency - starts out as 1/self.ts but then is updated to the real fs
        self.fastdata.fs = 1.0/self.ts

        # length of vectors

        self.num_samples_to_hold = int(self.time_to_display*1000/self.ts )
        if self.verbose:
            print(f"fastloop: num samples to hold = {self.num_samples_to_hold}")
        # this just holds a number which increments every time the loop runs
        # TODO get rid of this
        self.index = 0

        # should we try to do a realtime spline correction to the volume?
            # this makes the plots better but stresses the pi to do these calculations fast.
            # practical limit for this seems to be with loop clock at 25 ms

        self.correct_vol = correct_vol

        #define if we're inspiring or expiring
        self.insp = False
        self.exp = False

        if self.correct_vol:
            # slow down the loop so that it doesn't crash!
            if self.ts <= 25:
                self.ts = 25
            else:
                pass




        # Set up the sensor
        if self.simulation:
            self.sensor = sensor.fakesensor(main_path = self.main_path, verbose = self.verbose)
        else:
            self.sensor = sensor.sensor(main_path = self.main_path,verbose = self.verbose)
        
        
            
        # set up file to store sensor data
        if logdata:
            print('creating file to store cal data')
            filename = str(int(datetime.utcnow().timestamp()))
            self.sensor_datafile = open(filename + "_sensor_raw.txt","w")
            self.sensor_datafile.write('time \t p1 \t p2 \t dp')
        
        self.sensor.read()
        self.sensor.read()
        self.vol_integral_to_now = 0.0
        self.vol_offset = 0.0#self.sensor.dp2flow(self.sensor.dp)/(self.fastdata.fs*60.0)
        print('##### INITIAL VOLUME OFFSET = ',self.vol_offset)
        self.flow_drift_poly = None
        self.vol_drift_poly = None
        self.vol_concavity = None
        self.time_last_breath = 0
        self.time_last_exhale = 0
        
        
        
        
    def update_vol_offset(self):
        self.vol_offset = np.min(self.fastdata.vol)
        print('\n\n######## NEW VOLUME OFFSET = ',self.vol_offset,'\n\n')
        
    def update_flow_trend(self):
        flow_threshold = 5.0
        self.flow_drift_poly = np.polyfit(self.fastdata.t[np.abs(self.fastdata.flow_raw) < flow_threshold], self.fastdata.flow_raw[np.abs(self.fastdata.flow_raw) < flow_threshold],1)
        print(f'\nfastloop: Updated flow trend equation: F = {self.flow_drift_poly[0]}*t + {self.flow_drift_poly[1]} \n')
    
    def update_vol_trend(self):
        max_slope = 0.01
        
        # fit a line through the volume
        # we will remove this line and then add the offset (the minimum of the volume)
        self.vol_drift_poly = np.polyfit(self.fastdata.t, self.fastdata.vol_raw,1)
        if self.vol_drift_poly[1] > max_slope:
            self.vol_drift_poly[1] = max_slope
        elif self.vol_drift_poly[1] < (-1.0*max_slope):
            self.vol_drift_poly[1] = -1.0*max_slope
        self.vol_offset = np.min(self.fastdata.vol_raw - np.polyval(self.vol_drift_poly, self.fastdata.t))
        print(f'\n\nfastloop: Updated flow trend equation: V = {self.vol_drift_poly[0]}*t + {self.vol_drift_poly[1]}')
        #print(f'fastloop: volume offset = {self.vol_offset}\n\n')
        
        
    def restart_integral(self,time):
        
        
        
        integral_since_restart = np.sum(self.fastdata.vol_raw[self.fastdata.t > time])/(self.fastdata.fs*60.0)
        print('restarting the integral at time: ',time, ', sum since restart = : ',integral_since_restart)
        
        self.vol_integral_to_now = integral_since_restart
    
    def add_new_point(self,arr,new_point,maxlen):
        # adds a new data point to the array,
        # and keeps gets rid of the oldest point

        if len(arr) < maxlen:
            arr = np.append(arr,new_point)
        else:
            arr[:-1] = arr[1:]
            arr[-1] = new_point

        return arr

    def __del__(self):
        self.wait()

    def update(self):
        self.index +=1
        self.t_obj = datetime.utcnow()
        self.t = self.t_obj.timestamp()

        if self.verbose:
            # debugging: print an update of what we're doing
            print("\nfastloop: Index =  %d" % self.index)

        # record the update time
        self.update_time = datetime.utcnow()
        self.fastdata.t_obj = self.add_new_point(self.fastdata.t_obj, self.update_time, self.num_samples_to_hold)
        self.fastdata.t =     self.add_new_point(self.fastdata.t, self.update_time.timestamp(), self.num_samples_to_hold)
        self.fastdata.dt = self.fastdata.t - self.fastdata.t[0]

        # if there's at least two elements in the vector, calculate the real delta between samples
         # if there's at least two elements in the vector, calculate the real average delta between samples
        if len(self.fastdata.dt) >= 2:
            self.ts_real = np.abs(np.mean(self.fastdata.dt[1:] - self.fastdata.dt[:-1]))
            self.fastdata.fs = 1.0/self.ts_real



        # read the sensor pressure and flow data
        # there's probably a clenaer way to do this, but oh well...
        self.sensor.read()
        self.fastdata.p1   =    self.add_new_point(self.fastdata.p1,   self.sensor.p1,   self.num_samples_to_hold)
        self.fastdata.p2   =    self.add_new_point(self.fastdata.p2,   self.sensor.p2,   self.num_samples_to_hold)
        self.fastdata.dp   =    self.add_new_point(self.fastdata.dp,   self.sensor.dp,   self.num_samples_to_hold)
        #newflow = self.sensor.dp2flow(self.sensor.dp)
        
        self.fastdata.flow =    self.add_new_point(self.fastdata.flow, self.sensor.flow, self.num_samples_to_hold)
        
        #self.fastdata.flow_raw =    self.add_new_point(self.fastdata.flow_raw, newflow, self.num_samples_to_hold)
        #self.fastdata.flow = signal.detrend(self.fastdata.flow,type = 'constant')
        
        """
        # apply the linear fit to the stored flow data
        if not(self.flow_drift_poly is None):
            self.fastdata.flow = self.fastdata.flow_raw - np.polyval(self.flow_drift_poly,self.fastdata.t)
        else:
            self.fastdata.flow = np.copy(self.fastdata.flow_raw)
        """
        
        # build up a vector of the flow slope (ie the volume concavity)
        N = 50
        if len(self.fastdata.flow)> N:
            self.fastdata.dflow = self.add_new_point(self.fastdata.dflow,np.mean(self.fastdata.flow[-N+1:] - self.fastdata.flow[-N:-1]),self.num_samples_to_hold)
        else:
            self.fastdata.dflow = self.add_new_point(self.fastdata.dflow,0,self.num_samples_to_hold)
        
        
        """
        # build up the flow second derivative
        if len(self.fastdata.flow)> N:
            self.fastdata.d2flow = self.add_new_point(self.fastdata.d2flow,np.mean(self.fastdata.dflow[-N+1:] - self.fastdata.dflow[-N:-1]),self.num_samples_to_hold)
        else:
            self.fastdata.d2flow = self.add_new_point(self.fastdata.d2flow,0,self.num_samples_to_hold)
        """
        
        # if the flow and flow slope are below a threshold, AND we're not in the inspiratory phase, OR it's been too long since the last breath, then zero the volume)
        no_flow = (np.abs(self.fastdata.dflow[-1]) < 0.1) & (np.abs(self.fastdata.flow[-1]) < 5.0)
        not_expiratory_phase = (self.insp == False)
        too_long_since_last_breath = ((self.fastdata.t[-1] - self.time_last_breath)) > 10
        
        if (no_flow & not_expiratory_phase) or (too_long_since_last_breath):
            self.fastdata.vol_raw = self.add_new_point(self.fastdata.vol_raw, 0.0, self.num_samples_to_hold)
        else:
            self.fastdata.vol_raw = self.add_new_point(self.fastdata.vol_raw,self.fastdata.flow[-1]/(self.fastdata.fs*60.0)+self.vol_integral_to_now,self.num_samples_to_hold)
        
        # trigger a new breath if the slope flow is above a threshold and it's been long enough since the last breath
        started_inspiring = (self.fastdata.dflow[-1] > 0.25) & (self.fastdata.flow[-1] > 10.0)
        sufficient_time_since_last_breath =   (self.fastdata.t[-1] - self.time_last_breath) > 1.0                                   
        if (started_inspiring) & (sufficient_time_since_last_breath):
            self.insp = True   
            self.vol_integral_to_now = 0.0
            self.time_last_breath = self.fastdata.t[-1]
            #beep()
            print("\n\n\nfastloop: #### NEW INHALE ####\n\n\n")
            self.new_inhale.emit()
            
            # mark the current time as the end of exhalation
            self.breathdata.tee = self.fastdata.t[-1]
            
            # blast out the new breath data to main
            self.new_breath.emit(self.breathdata)
            
            # reset the data in the current breath
            self.breathdata.reset()
            # mark the time of the start of inspiration
            self.breathdata.tsi = self.fastdata.t[-1]
            
        else:
            self.vol_integral_to_now = self.fastdata.vol_raw[-1]
        
        # trigger the end of inspiration
        if (self.fastdata.dflow[-1] < -0.25) & (self.fastdata.flow[-1] < -10.0) & ((self.fastdata.t[-1] - self.time_last_exhale)>1.0):
            self.insp = False
            self.time_last_exhale = self.fastdata.t[-1]
            #self.new_exhale.emit()
            print("\n\n\nfastloop: #### NEW EXHALE ####\n\n\n")
            # mark the time of the end of inspiration
            self.breathdata.tei = self.fastdata.t[-1]
            
            
        self.fastdata.insp = self.add_new_point(self.fastdata.insp, self.insp, self.num_samples_to_hold)    
        
        #    self.vol_concavity = np.mean(np.gradient(np.gradient(self.fastdata.vol_raw[-10:])))
        # 
        #    if self.vol_concavity > 0:
        #        #beep()
        
        
        #self.fastdata.flow = signal.detrend(self.fastdata.flow,type = 'constant')
        #self.fastdata.vol_raw = self.add_new_point(self.fastdata.vol_raw, (np.sum(self.fastdata.flow) + self.vol_integral_to_now)/(self.fastdata.fs*60.0),self.num_samples_to_hold)
        #self.fastdata.vol_raw = integrate.cumtrapz(self.fastdata.flow, initial = self.vol_integral_to_now)/(self.fastdata.fs*60.0)
        #self.fastdata.vol_raw = signal.detrend(self.fastdata.vol_raw)
        

        #dp_zero = np.mean(self.fastdata.dp[np.abs(self.fastdata.dp)<0.0])
        #if np.isnan(dp_zero):
        #    dp_zero = 0.0

        #flow_zero = self.sensor.dp2flow(dp_zero)

        #self.fastdata.dp[np.abs(self.fastdata.dp)<0.0] = 0.0

        #self.fastdata.flow = self.sensor.dp2flow(self.fastdata.dp)# - flow_zero

        # apply a median filter
        #self.fastdata.flow = signal.medfilt(self.fastdata.flow,3)

        # log the data if we're in logdata mode
        if self.logdata:
            self.log_raw_sensor_data()

        # calculate the raw volume
        #self.fastdata.vol_raw = np.cumsum(self.fastdata.flow)/(self.fastdata.fs*60.0)
        #self.fastdata.vol_raw = signal.detrend(self.fastdata.vol_raw)

        if self.correct_vol:
            try:
                # correct the detrended volume signal using the slowdata spline fit
                self.apply_vol_corr()
            except Exception as e:
                print("fastloop: error in volume spline correction: ",e)
                print("fastloop: could not apply vol spline correction. using raw volume instead...")
                self.fastdata.vol = self.fastdata.vol_raw
                self.fastdata.vol_drift = 0.0*self.fastdata.vol_raw

        else:
            if self.vol_drift_poly is None:
                self.fastdata.vol_drift = 0.0*np.copy(self.fastdata.vol_raw)
            else:
                self.fastdata.vol_drift = np.polyval(self.vol_drift_poly,self.fastdata.t)
            
            self.fastdata.vol = self.fastdata.vol_raw - self.fastdata.vol_drift - self.vol_offset
            
            
        
        # tell the newdata signal to emit every time we update the data
        self.newdata.emit(self.fastdata)

        # send data to the datafiller
        self.fastdata.all_fields.update({'pressure' : self.fastdata.p1[-1]})
        self.fastdata.all_fields.update({'flow' : self.fastdata.flow[-1]})
        #self.fastdata.all_fields.update({'volume' : self.fastdata.vol[-1]*1000 - self.vol_offset}) # in mL
        self.fastdata.all_fields.update({'volume' : self.fastdata.vol[-1]*1000}) # in mL

        
        # fill the data in the breathdata object
        self.breathdata.p       = add_new_point(self.breathdata.p,      self.fastdata.p1[-1],                   self.num_samples_to_hold)
        self.breathdata.flow    = add_new_point(self.breathdata.flow,   self.fastdata.flow[-1],                 self.num_samples_to_hold)
        self.breathdata.vol     = add_new_point(self.breathdata.vol,    self.fastdata.vol[-1]*1000,             self.num_samples_to_hold)
        self.breathdata.dt      = add_new_point(self.breathdata.dt,     self.fastdata.t[-1] - self.breathdata.tsi,  self.num_samples_to_hold)

    def log_raw_sensor_data(self):

        self.sensor_datafile.write('%f \t %f \t %f \t %f\n' %(self.fastdata.t[-1],self.fastdata.p1[-1],self.fastdata.p2[-1],self.fastdata.dp[-1]))


    def apply_vol_corr(self):
        # this uses the current volume minima spline calculation to correct the volume by pinning all the minima to zero
        if len(self.fastdata.vol_raw) >= 10:
            i_min = utils.breath_detect_coarse(-1.0*self.fastdata.vol_raw,self.fastdata.fs,minpeak = 0.05)
        else:
            i_min = []

        if self.verbose:
            print(f"fastloop: found {len(i_min)} volume minima at dt = {self.fastdata.dt[i_min]}")
        if len(i_min) >= 2:
            self.fastdata.vol_corr_spline = interpolate.interp1d(self.fastdata.t[i_min],self.fastdata.vol_raw[i_min],kind = 'linear',fill_value = 'extrapolate')
            self.fastdata.vol_drift = self.fastdata.vol_corr_spline(self.fastdata.t)
        else:
            self.fastdata.vol_drift = np.zeros(len(self.fastdata.vol_raw))
        # apply the correction
        self.fastdata.vol = self.fastdata.vol_raw - self.fastdata.vol_drift


    def run(self):
        if self.verbose:
            print("fast loop: starting fast Loop")
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.ts)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.exec() # YOU NEED THIS TO START UP THE THREAD!

        # NOTE: only QThreads have this exec() function, NOT QRunnables
        # If you don't do the exec(), then it won't start up the event loop
        # QThreads have event loops, not QRunnables

        """
        # NOTE: only QThreads have this exec() function, NOT QRunnables
        #       If you don't do the exec(), then it won't start up the event
        #       loop QThreads have event loops, not QRunnables

        # Source: https://doc.qt.io/qtforpython/overviews/timers.html
        Quote:
          In multithreaded applications, you can use the timer mechanism in any
          thread that has an event loop. To start an event loop from a non-GUI
          thread, use exec()

        """


class slow_loop(QtCore.QThread):

    # define a new signal that will be used to send updated data back to the main thread
    # this signal returns an object that holds the data to ship out to main
    new_slowdata = QtCore.pyqtSignal(object)
    new_breathpar = QtCore.pyqtSignal(object)
    
    # this signal sends a request to the mainloop to get the current data from the fastloop
    request_fastdata = QtCore.pyqtSignal()
    
    #breath detected signal
    breath_detected = QtCore.pyqtSignal(float) #returns the time the breath was detected
    
    def __init__(self, main_path, config, verbose = False):
        QtCore.QThread.__init__(self)

        # print stuff for debugging?
        self.verbose = verbose

        # get the main path
        self.main_path = main_path
        if self.verbose:
            print(f"slowloop: main path = {self.main_path}")

        # run in verbose mode?
        self.verbose = verbose

        self.config = config
        #self.data_filler = data_filler

        # this just holds a number which increments every time the loop runs
        # TODO get rid of this
        self.index = 0

        # set up a place to store the data that comes in from the fast loop each time this loop runs
        self.fastdata = fast_data()

        # set up a place to store the slow data that is calculated each time this loop runs
        self.slowdata = slow_data()

        # set up a place to store the data from the last breath
        self.breathdata = breath_data()        

        # set up a place to store the breath parameters calculated from the last breath
        self.breathpar = breath_par()

        # note the time the loop is executed
        self.t_obj = datetime.utcnow()
        self.t = self.t_obj.timestamp()
        self.t_last_prev = 0
        
        # the time the slowloop was created
        self.t_created = np.copy(self.t)
        
        # time between samples
        self.ts = self.config['slowdata_interval'] #ms

        # loop sample frequency - starts out as 1/self.ts but then is updated to the real fs
        self.fs = 1.0/self.ts

        # the indices of the volume minima
        self.i_min_vol = []

        # times from the last breath
        self.tsi = self.t # start time of inspiration (absolute time)
        self.dtsi = [] # start time of inspiration (dt since start)
        self.dtei = [] # end time of inspiration (dt since start)
        self.dtee = [] # end time of expiration (dt since start)

        # set up the raspberry pi GPIO THESE ARE BCM -- OTHERWISE THERE'S A CONFLICT IF YOU USE BOARD
        # WHY?  I think that the pressure sensor module must be setting it somewhere.
        # BCM is better anyways, it's the numbers of the inputs not the pins!
        self.gpio_map = {'charging':5, 'lowbatt':4}

        try:
            if True:
                print(f"GPIO mode = {GPIO.getmode()}")
            GPIO.setmode(GPIO.BCM)

            for key in self.gpio_map.keys():
                if True:
                    print(f"slowloop: setting GPIO key: {key}")
                GPIO.setup(self.gpio_map[key],GPIO.IN)
                #time.sleep(1)
        except Exception as e:
            print('slowloop: unable to set up Pi GPIO: ',e)

    def __del__(self):
        self.wait()

    def update(self):
        """
        ### This is the slow loop ####

        Here's what we want to do:

            1. Calculate the correction to the volume signal
                # calibrations
                self.slowdata.vol_corr_spline = np.array([])
                self.slowdata.vol_drift_params = np.array([])
            2. fit the mimima and maxima of the volume signal using peak finder
            3. calculate the breath parameters of the last breath:
        """


        

        self.index +=1
        if self.verbose:
            print("\nslowloop: %d" % self.index)

        # emit the request data signal to get the current fastloop data vectors
        self.request_fastdata.emit()
        
        
        
        # only do all this effort if there's actually data received from the fastloop:
        if len(self.fastdata.p1 > 0):
            #print("slowloop: executing loop")
            # note the time the loop is executed
            self.t_obj = datetime.utcnow()
            self.t = self.t_obj.timestamp()
            
            """
            # try to fit a spline
            try:
                # find the volume minima
                self.find_vol_min()

                # calculate breath parameters
                #self.calculate_breath_params()
            except Exception as e:
                print("slowloop: vol min calc error: ",e)
            
            
            # try to calculate the breath parameters
            try:
                self.calculate_breath_params()

            except Exception as e:
                print("slowloop: error calculating breath parameters: ",e)
            

            # Do these whether or not a breath is detected!
            # how long ago was the last breath started?
            
            self.slowdata.dt_last = (self.t - self.slowdata.t_last)
            """
            # how long since the last breath
            self.slowdata.dt_last = (self.t - self.slowdata.t_last)
            
            # now measure the realtime value (it fluctuates but stays near the real value, and is valuable if no breaths are delivered)
                # we don't display a full minute so need to scale answer
            scale = 60.0/self.fastdata.dt[-1]
            flow_in = self.fastdata.flow[self.fastdata.flow > 0]
            flow_out = self.fastdata.flow[self.fastdata.flow < 0]
            mve_meas_in = np.abs(np.trapz(flow_in)/(self.fastdata.fs*60.0)*scale)
            mve_meas_out = np.abs(np.trapz(flow_out)/(self.fastdata.fs*60.0)*scale)
            #average the flow in and out to get a sensible result regardless of flow sensor drift
            self.slowdata.mve_meas = ( np.mean([mve_meas_in, mve_meas_out]))


            self.check_power()


            # tell main that there's new slow data: emit the newdata signal
            self.new_slowdata.emit(self.slowdata)
        else:
            pass


    def check_power(self):
        # Recall: self.gpio_map = {'charging':7, 'lowbatt':29}
        # try to check the power status
        try:
            self.slowdata.lowbatt  = GPIO.input(self.gpio_map['lowbatt'])
            self.slowdata.charging = GPIO.input(self.gpio_map['charging'])

        except Exception as e:
            print("slowloop: could not check power state: ",e)

    def find_vol_min(self):
        """
        ## find the min of the volume signal using peak finder ##

        """
        # step 0: detrend the volume
        self.fastdata.vol = signal.detrend(self.fastdata.vol)
        
        # step 1: find index of min and max
        self.i_min_vol = utils.breath_detect_coarse(-1*self.fastdata.vol, fs = self.fastdata.fs,minpeak = 0.0)

        if self.verbose:
            print(f"slowloop: found {len(self.i_min_vol)} peaks at dt = {self.fastdata.dt[self.i_min_vol]}")


    def calculate_breath_params(self):
        """
        
        This calcuates the breath parameters from the last breath,
        which is the data that has been passed to it from the fastloop as
        the "breathdata" object:
            
        ## BREATH DATA OBJECT HOLDS:
        self.p      =   pressure waveform during last breath
        self.flow   =   flow waveform during last breath
        self.vol    =   volume waveform during last breath
        self.dt     =   time during last breath (in seconds) since start of breath
        self.tsi    =   absolute time of start of inspriation
        self.tei    =   absolute time of end of inspriation
        self.tee    =   absolute time of end of expriration
        
        This blindly assumes that the breath data is for a good breath, and 
        goes ahead with the calculation. 

        The function populates the following values in the slowdata object:

        ## THINGS THAT HOLD SINGLE VALUES ##
        # respiratory parameters from last breath
        self.pip = []
        self.peep = []
        self.pp = []
        self.vt = []
        self.mve = []
        self.rr = []
        self.ie = []
        self.c = []
        
        
        After recalcuating the breath parameters, it signals to the main loop
        that there is new slowloop data.
        """
        print('slowloop: trying to calculate breath params')
        if len(self.breathdata.p)>0:
            # calculate the relative times of the end of inspriation and the end of expiration
            self.dtsi = 0.0
            self.dtei = self.breathdata.tei - self.breathdata.tsi
            self.dtee = self.breathdata.tee - self.breathdata.tsi
            
            # record the time of the last breath
            self.slowdata.t_last = self.breathdata.tee
            
            # get tidal volume (in mL) and the end inspiration time (both defined at vol peak over last breath)
            self.breathpar.vt = np.max(self.breathdata.vol)
            
            # get pip: peak pressure over last breath
            self.breathpar.pip = np.max(self.breathdata.p)
        
            # get respiratory rate (to one decimal place)
            self.breathpar.rr = (60.0/(self.breathdata.tee - self.breathdata.tsi))
        
            # get i:e ratio (to one decimal place)
            dt_exp = self.breathdata.tee - self.breathdata.tei
            dt_insp = self.breathdata.tei - self.breathdata.tsi
            self.breathpar.ie = np.abs(dt_exp) / np.abs(dt_insp)
            
            #print('slowloop: tsi = ',self.breathdata.tsi)
            #print('slowloop: tei = ',self.breathdata.tei)
            #print('slowloop: tee = ',self.breathdata.tee)
            
            # get minute volume
            # first infer it from the last breath: RR * VT
            self.breathpar.mve_inf = ( (self.breathpar.rr * self.breathpar.vt/1000.0))
            
            # get peep: average pressure over the 50 ms about the end of expiration
            dt_peep = 0.05
            self.breathpar.peep =  np.mean(self.breathdata.p[(self.breathdata.dt>=self.dtee-(dt_peep))])
            
            # get pp: plateau pressure -- defined as mean pressure over 50 ms before the end of inspiration
            dt_pip = 0.05
            self.breathpar.pp = (np.mean(self.breathdata.p[(self.breathdata.dt>=self.dtei-dt_pip) & (self.breathdata.dt<=self.dtei)]))
            
            # get static lung compliance. Cstat = VT/(PP - PEEP), reference: https://www.mdcalc.com/static-lung-compliance-cstat-calculation#evidence
            self.breathpar.c = ( self.breathpar.vt/(self.breathpar.pp - self.breathpar.peep))
            
            self.new_breathpar.emit(self.breathpar)
        else:
            print('slowloop: no breathdata to calculate breath parameters on')

    def calculate_breath_params_from_fastdata(self):
        """

        ## THINGS THAT HOLD SINGLE VALUES ##
        # respiratory parameters from last breath
        self.pip = []
        self.peep = []
        self.pp = []
        self.vt = []
        self.mve = []
        self.rr = []
        self.ie = []
        self.c = []
        """
        print('slowloop: trying to calculate breath params')
        
        if len(self.i_min_vol) >= 2:
            # define the last breath
            self.tsi = self.fastdata.t[self.i_min_vol[-2]]
            self.tee = self.fastdata.t[self.i_min_vol[-1]]
            self.dtsi = self.fastdata.dt[self.i_min_vol[-2]]
            self.dtee = self.fastdata.dt[self.i_min_vol[-1]]

            # update the time of the last breath
            self.slowdata.t_last = ( self.tee )
            #print(f'slowloop: self.slowdata.t_last = {self.slowdata.t_last}, self.t_last_prev = {self.t_last_prev}, delta = {self.slowdata.t_last - self.t_last_prev}')
            #if the "last breath" has changed by more than some threshold time, it's a new breath
            if (self.slowdata.t_last - self.t_last_prev) > 0.5:
                self.slowdata.newbreath_detected = True
                print('slowloop: new breath detected')
                self.t_last_prev = self.slowdata.t_last
            else:
                #self.dt_last_prev = self.slowdata.t_last
                self.slowdata.newbreath_detected = False
                print('slowloop: NO new breath detected')
            # index range of the last breath
            index_range = np.arange(self.i_min_vol[-2],self.i_min_vol[-1]+1)


            # get tidal volume (in mL) and the end inspiration time (both defined at vol peak over last breath)
            self.slowdata.vt = ( np.max(self.fastdata.vol[index_range])*1000)
            self.i_max_vol_last = index_range[np.argmax(self.fastdata.vol[index_range])]
            self.dtei = self.fastdata.dt[self.i_max_vol_last]

            # get pip: peak pressure over last breath
            self.slowdata.pip = ( np.max(self.fastdata.p1[index_range]))
            
           
            # get respiratory rate (to one decimal place)
            self.slowdata.rr = (60.0/(self.dtee - self.dtsi))

            # get i:e ratio (to one decimal place)
            dt_exp = self.dtee - self.dtei
            dt_insp = self.dtei - self.dtsi
            self.slowdata.ie = ( np.abs(dt_exp / dt_insp))

            # get minute volume
            # first infer it from the last breath: RR * VT
            self.slowdata.mve_inf = ( (self.slowdata.rr * self.slowdata.vt/1000.0))


            # get peep: average pressure over the 50 ms about the end of expiration
            dt_peep = 0.05
            self.slowdata.peep = ( np.mean(self.fastdata.p1[(self.fastdata.dt>=self.dtee-(dt_peep/2)) & (self.fastdata.dt<=self.dtee+(dt_peep/2))]))

            # get pp: plateau pressure -- defined as mean pressure over 50 ms before the end of inspiration
            dt_pip = 0.05
            self.slowdata.pp = (np.mean(self.fastdata.p1[(self.fastdata.dt>=self.dtei-dt_pip) & (self.fastdata.dt<=self.dtei)]))

            # get static lung compliance. Cstat = VT/(PP - PEEP), reference: https://www.mdcalc.com/static-lung-compliance-cstat-calculation#evidence
            self.slowdata.c = ( self.slowdata.vt/(self.slowdata.pp - self.slowdata.peep))

            """
            # round the pip and peep and vt
            self.slowdata.pip = np.round(self.slowdata.pip,1)
            self.slowdata.peep = np.round(self.slowdata.peep,1)
            self.slowdata.pp = np.round(self.slowdata.pp,1)
            self.slowdata.vt = np.round(self.slowdata.vt,1)
            """
                
            


        else:
            print("slowloop: no breath detected!")



    def update_fast_data(self,fastdata):
        # this is a slot connected to mainwindow.newrequest
        # this takes the fastdata from the main window and updates the internal value of fastdata
        self.fastdata = fastdata

        if self.verbose:
            print(f"slowloop: received new fastdata from main (updated at {self.fastdata.t[-1]}, fs = {self.fastdata.fs} Hz")

    def update_breath_data(self,breath_data):
        self.breathdata = breath_data
        
        if self.verbose:
            print(f"slowloop: received new breathdata from main (breath started at {self.breathdata.tee})")


    def run(self):
        if self.verbose:
            print("slowloop: starting slowloop")
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.ts)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.exec() # YOU NEED THIS TO START UP THE THREAD!
        # NOTE: only QThreads have this exec() function, NOT QRunnables
        # If you don't do the exec(), then it won't start up the event loop
        # QThreads have event loops, not QRunnables
        """
        # NOTE: only QThreads have this exec() function, NOT QRunnables
        #       If you don't do the exec(), then it won't start up the event
        #       loop QThreads have event loops, not QRunnables

        # Source: https://doc.qt.io/qtforpython/overviews/timers.html
        Quote:
          In multithreaded applications, you can use the timer mechanism in any
          thread that has an event loop. To start an event loop from a non-GUI
          thread, use exec()

        """