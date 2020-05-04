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

# add the wsp directory to the PATH
main_path = os.path.dirname(os.getcwd())
sys.path.insert(1, main_path)

# import custom modules
from sensor import sensor
from utils import utils

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
        
        # volume
        self.vol = np.array([])
        
        # time
        self.time = np.array([])
        self.dt = np.array([])
        
        # pi GPIO state
        self.lowbatt = False
        self.charging = True
        
class slow_data(object):
    def __init__(self):
        
        ## THINGS THAT HOLD ARRAYS ##
        # times of the volume min and max
        self.vmin_times = np.array([])
        self.vmax_times = np.array([])
        
        # calibrations
        self.vol_corr_spline = np.array([])
        self.vol_drift_params = np.array([])
        
        ## THINGS THAT HOLD SINGLE VALUES ##
        # times from the last breath
        self.tsi = [] # start time of inspiration
        self.tei = [] # end time of inspiration
        self.tse = [] # start time of expiration (same as tei)
        self.tee = [] # end time of expiration
        
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
    
    def __init__(self, main_path = main_path,time_to_display = 20.0,verbose = False):
        
        QtCore.QThread.__init__(self)
        
        # run in verbose mode?
        self.verbose = verbose
        
        # time to display is the approx time to show on the screen in seconds
        self.time_to_display = time_to_display #s
        
        # time between samples
        self.dt = 1000 #ms
        
        # sample frequency - starts out as 1/self.dt but then is updated to the real fs 
        self.fs = 1.0/self.dt
        
        # length of vectors
        self.num_samples_to_hold = int(self.time_to_display*1000/self.dt)
        
        # this just holds a number which increments every time the loop runs
        # TODO get rid of this
        self.index = 0
        
        
        # Define the instance of the object that will hold all the data
        self.fastdata = fast_data()
        
        # Set up the sensor
        self.sensor = sensor.sensor(main_path = main_path,verbose = self.verbose)
        
        # Correction equations:
        # Line to fit the flow drift - will hold polynomial fit parameters
        self.vol_drift_params = []
        
        # spline curve to fit the volume minima
        self.vol_corr_spline = []
        self.tcal_min # minimum time over which the spline curve applies
        self.tcal_max # maximum time overwhich the spline curve applies
        
        
    def add_new_point(arr,new_point,maxlen):
        # adds a new data point to the array,
        # and keeps gets rid of the oldest point
        if len(arr) < maxlen:
            np.append(arr,new_point)
        else:
            arr[:-1] = arr[1:]
            arr[-1] = new_point

    
    def __del__(self):
        self.wait()
    
    def update(self):
        self.index +=1
        
        if self.verbose:
            # debugging: print an update of what we're doing
            if (self.index % 2) == 0:
                #Then it's even
                print("fast loop: Index =  %d" % self.index)
            
        # record the update time
        self.time = datetime.utcnow()
        
        # read the sensor pressure and flow data
        self.sensor.read()
        self.add_new_point(self.fastdata.p1,  self.sensor.p1,   self.num_samples_to_hold)
        self.add_new_point(self.fastdata.p2,  self.sensor.p2,   self.num_samples_to_hold)
        self.add_new_point(self.fastdata.dp,  self.sensor.dp,   self.num_samples_to_hold)
        self.add_new_point(self.fastdata.flow,self.sensor.flow, self.num_samples_to_hold)
        
        # calculate the volume
        # volume is in liters per minute! so need to convert fs from (1/s) to (1/m)
            # fs (1/min) = fs (1/s) * 60 (s/min)
        vol_raw_last = np.sum(self.flow)/(self.fs*60.0) # the sum up to now. This way we don't have to calculate the cumsum of the full array
        self.add_new_point(self.fastdata.vol_raw,vol_raw_last,self.num_samples_to_hold)
        
        if self.verbose:
            # debugging: print the sensor dP
            print (f"fast loop: dP = {self.sensor.dp}")
            
        # tell the newdata signal to emit every time we update the data
        self.newdata.emit(self.fastdata)
    
    def update_cal(self):
        """
        This updates the volume calibration spline. It's triggered whenever
        the slow loop executes. It does the following:
            1. update the spline curve
            2. update the min and max times overwhich the calibration applies
        """
        
        if self.verbose:
            print("fastloop: Updating Calibration")
            
    def correct_vol(self):
        # this uses the current volume minima spline calculation to correct
        # the volume by pinning all the minima to zero
        
        if self.verbose:
            print("fastloop: correcting volume")
        
        # step 1: detrend the raw volume
        
        # step 2: use the spline to correct the volume
        
    
    
    def run(self):
        if self.verbose:
            print("fast loop: starting fast Loop")
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
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
    newdata = QtCore.pyqtSignal(object)
    
    def __init__(self,verbose = False):
        QtCore.QThread.__init__(self)
        #self.n = input("  Enter a number to count up to: ")
        self.index = 0
        
        # print stuff for debugging?
        self.verbose = verbose
        
        # set up a place to store the data that comes in from the fast loop each time this loop runs
        self.fastdata = fast_data()
        
        # set up a place to store the slow data that is calculated each time this loop runs
        self.slowdata = slow_data()
        
    def __del__(self):
        self.wait()
    
    def update(self):
        self.index +=1
        if self.verbose:
            if (self.index % 2) == 0:
                #Then it's even
                print("slowloop: %d" % self.index)
    
        # emit the newdata signal
        self.newdata.emit(self.slowdata)
    
    
    
    
    
    
    def run(self):
        print("Starting 1 Hz Loop")
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
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
