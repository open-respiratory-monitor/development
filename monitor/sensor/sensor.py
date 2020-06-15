#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May  3 16:59:47 2020

sensor.py

This defines a sensor class which initializes the pressure sensors and
can poll the sensors.

@author: nlourie
"""

#from datetime import datetime
#import numpy as np
#from scipy import signal

import time
import numpy as np
import sys
import os



#load the sensor board modules:
try:
    import board
    import busio
    import adafruit_lps35hw  # pressure sensor
    import adafruit_tca9548a # i2c mux
except Exception as e:
    print("could not load sensor board modules: ",e)

# add the main directory to the PATH
main_path = os.path.dirname(os.getcwd())
sys.path.insert(1, main_path)


class sensor(object):

    """
    Constituents:
        sensor1 = pressure sensor #1
        sensor2 = pressure sensor #2
        
        # pressure on either side of flow restrictor/sensor
        p1 = pressure @ sensor 1 in cmH20 with respect to ambient
        p2 = pressure @ sensor 2 in cmH20 with respect to ambient
        
        # ambient pressure, not in airway
        p3 = pressure @ sensor 3 in cmH20 
        
        
        dp = differential pressure (p2 - p1) in cmH20
        flow = flow in slpm
    """

    def __init__(self,main_path, mouthpiece = 'hamilton',dp_thresh = 0.0,verbose = False):

        # run in verbose mode?
        self.verbose = verbose

        self.dp_thresh = dp_thresh

        # Initialize the i2c bus
        self.i2c = busio.I2C(board.SCL, board.SDA)

        # Using the adafruit_lps35hw class to read in the pressure sensor
            # note the address must be in decimal.
            # allowed addresses are:
                # 92 (0x5c - if you put jumper from SDO to Gnd)
                # 93 (0x5d - default)
        
        # set up the i2c multiplexer    
        self.i2cmux = adafruit_tca9548a.TCA9548A(self.i2c)
        
        # Set up the sensors
        self.sensor2 = adafruit_lps35hw.LPS35HW(self.i2c, address = 92)
        self.sensor1 = adafruit_lps35hw.LPS35HW(self.i2c, address = 93)
        self.sensor3 = adafruit_lps35hw.LPS35HW(self.i2cmux[0]) # this sensor is plugged into the mux on ch 0
        
        self.sensor1.data_rate = adafruit_lps35hw.DataRate.RATE_75_HZ
        self.sensor2.data_rate = adafruit_lps35hw.DataRate.RATE_75_HZ
        self.sensor3.data_rate = adafruit_lps35hw.DataRate.RATE_75_HZ
        
        self.sensor1.low_pass_enabled = True
        self.sensor2.low_pass_enabled = True
        self.sensor3.low_pass_enabled = True
        
        # Load the flow calibration polynomial coefficients
        self.main_path = main_path


        # define the calibration file based on the mouthpiece
        self.set_mouthpiece(mouthpiece)
        
                

        # Define the unit conversion factor
        self.mbar2cmh20 = 1.01972

        # Load the flow calibration polynomial coefficients
        self.main_path = main_path

        # initial offsets are zero
        self.p1_offset = 0.0
        self.p2_offset = 0.0
        self.p_ambient = 0.0

        # holds info about whether the sensor is initialized
        self.initialized = False
        
        
        # no flow offset initially
        self.dp_offset = 0.0
        
        # Zero the sensors
        self.rezero()
        
        
        
        # Initialize the class values
        self.read()
        
    def set_mouthpiece(self,mouthpiece):
        # define the calibration file based on the mouthpiece
        self.mouthpiece = mouthpiece
        print('sensor: set calibration to: ',self.mouthpiece)
        if self.mouthpiece.lower() == 'hamilton':
            self.calfile = '/calibration/flow_calibration_hamilton.txt'
        elif self.mouthpiece.lower() == 'iqspiro':
            self.calfile = '/calibration/flow_calibration_iqspiro.txt'
        else:
            raise ImportError('specified mouthpiece not defined')
        
        # now load the calibration data for the mouthpiece
        self.flowcal = np.loadtxt(self.main_path + self.calfile,delimiter = '\t',skiprows = 1)
            
    def dp2flow(self,dp_cmh20):
        flow_sign = np.sign(dp_cmh20)
        flow = flow_sign*np.polyval(self.flowcal,np.abs(dp_cmh20))
        return flow
    
    def update_ambient_pressure(self):
        samples = 5
        #rechecks the ambient pressure
        p3_arr = []
        for i in range(samples):
            p3_arr.append((self.sensor3.pressure))
        p3_arr = np.array(p3_arr)
        self.p_ambient = np.mean(p3_arr)*self.mbar2cmh20

    def rezero(self, samples = 100):
        # Zeroes the sensors
        # Just takes the current readings and sets them to zero pressure for
        # each sensor
        """
        # Now read out the pressure difference between the sensors
        print('p1_0 = ',self.sensor1.pressure,' mbar')
        print('p1_0 = ',self.sensor1.pressure*self.mbar2cmh20,' cmH20')
        print('p2_0 = ',self.sensor2.pressure,' mbar')
        print('p2_0 = ',self.sensor2.pressure*self.mbar2cmh20,' cmH20')

        print('')
        print('Now zero the pressure:')
        # Not sure why sometimes I have to do this twice??
        self.sensor1.zero_pressure()
        self.sensor1.zero_pressure()
        time.sleep(1)
        self.sensor2.zero_pressure()
        self.sensor2.zero_pressure()
        time.sleep(1)
        print('p1_0 = ',self.sensor1.pressure,' mbar')
        print('p1_0 = ',self.sensor1.pressure*self.mbar2cmh20,' cmH20')
        print('p2_0 = ',self.sensor2.pressure,' mbar')
        print('p2_0 = ',self.sensor2.pressure*self.mbar2cmh20,' cmH20')
        print()
        """
        p1_arr = []
        p2_arr = []
        p3_arr = []
        
        # needs this sleep! otherwise the first samples are bad and the offset comes out wrong
        time.sleep(2)
        print(f'sensor: taking {samples} samples to determine ambient pressure...')
        for i in range(samples):
            p1_arr.append((self.sensor1.pressure))
            p2_arr.append((self.sensor2.pressure))
            p3_arr.append((self.sensor3.pressure))
        p1_arr = np.array(p1_arr)
        p2_arr = np.array(p2_arr)
        p3_arr = np.array(p3_arr)
            
        # get the mean ambient pressure
        self.p_ambient = np.mean(p3_arr)*self.mbar2cmh20
        
        #set he offset to the mean pressure    
        self.p1_offset = np.mean(p1_arr)*self.mbar2cmh20 - self.p_ambient
        self.p2_offset = np.mean(p2_arr)*self.mbar2cmh20 - self.p_ambient
        
        
        # print what's happening
        print(f'sensor: P1 offset = {self.p1_offset}')
        print(f'sensor: P2 offset = {self.p2_offset}')
        
        self.read()
        print(f'P1 Corr = {self.p1}')
        print(f'P2 Corr = {self.p2}')
        self.initialized = True
        
        
    def set_zero_flow(self,samples_to_average = 100):
        dp_arr = []
        for i in range(samples_to_average):
            self.read()
            dp_arr.append(self.dp)
        self.dp_offset = np.mean(dp_arr)
        
        
    def read(self):
        
        
        
        # Read the pressure sensors and update the values, the pressures are differential with respect to p3
        self.p1 = (self.sensor1.pressure * self.mbar2cmh20) - self.p_ambient - self.p1_offset
        self.p2 = (self.sensor2.pressure * self.mbar2cmh20) - self.p_ambient - self.p2_offset
        
        dp = (self.p2 - self.p1) - self.dp_offset
                
        self.dp = dp 

        # Calculate the flow
        self.flow = self.dp2flow(self.dp)


class fakesensor(object):
    # if we're in simulation mode, then instead of using a real sensor, just
    # read in old data like it's real data.
    """
    Constituents:
        sensor1 = pressure sensor #1
        sensor2 = pressure sensor #2

        p1 = pressure @ sensor 1 in cmH20
        p2 = pressure @ sensor 2 in cmH20
        dp = differential pressure (p2 - p1) in cmH20
    """

    def __init__(self,main_path, mouthpiece = 'iqspiro',datafile = '/calibration/Simulated_Data.txt',dp_thresh = 0.0,verbose = False):
        #datafile = '/calibration/1590534414_sensor_raw.txt'
        self.datafile = main_path + datafile
        self.verbose = verbose
        self.time_arr,self.p1_arr,self.p2_arr,self.dp_arr = np.loadtxt(self.datafile,delimiter = '\t',skiprows = 100,unpack = True)
        
        self.linenum = 0
        
        self.lastline = len(self.time_arr)-1
        
        # Load the flow calibration polynomial coefficients
        self.main_path = main_path
        
        # define the calibration file based on the mouthpiece
        self.set_mouthpiece(mouthpiece)

        # initial offsets are zero
        self.p1_offset = 0.0
        self.p2_offset = 0.0        
        
        
        # start out with the sensor inmitialized
        self.initialized = True
        
        # Define the unit conversion factor
        self.mbar2cmh20 = 1.01972

        # Load the flow calibration polynomial coefficients
        self.main_path = main_path

        
        #print statement
        print(f"Reading Simulated Data from File: {self.datafile}")

        # no flow offset initially
        self.dp_offset = 0.0
        
        
    def set_mouthpiece(self,mouthpiece):
        # define the calibration file based on the mouthpiece
        self.mouthpiece = mouthpiece
        print('sensor: set calibration to: ',self.mouthpiece)
        if self.mouthpiece.lower() == 'hamilton':
            self.calfile = '/calibration/flow_calibration_hamilton.txt'
        elif self.mouthpiece.lower() == 'iqspiro':
            self.calfile = '/calibration/flow_calibration_iqspiro.txt'
        else:
            raise ImportError('specified mouthpiece not defined')
        
        # now load the calibration data for the mouthpiece
        self.flowcal = np.loadtxt(self.main_path + self.calfile,delimiter = '\t',skiprows = 1)
            
    def dp2flow(self,dp_cmh20):
        flow_sign = np.sign(dp_cmh20)
        flow = flow_sign*np.polyval(self.flowcal,np.abs(dp_cmh20))
        return flow

    def rezero(self):
        self.p1_offset = self.p1
        self.p2_offset = self.p2
        
        
        
    def set_zero_flow(self,samples_to_average = 100):
        dp_arr = []
        for i in range(samples_to_average):
            self.read()
            dp_arr.append(self.dp)
        self.dp_offset = np.mean(dp_arr)

    def read(self):

        # read the fake data from the current line
        self.p1 = self.p1_arr[self.linenum] - self.p1_offset
        self.p2 = self.p2_arr[self.linenum] - self.p2_offset
        self.dp = (self.p2 - self.p1) - self.dp_offset
        # Calculate the flow
        self.flow = self.dp2flow(self.dp)
        # increment the line number
        self.linenum += 1

        # start again if you hit the end of the file
        if self.linenum >= self.lastline:
            self.linenum = 0


if __name__ == "__main__":
    try:
        print("Loading real sensor...")
        sensor = sensor(main_path = main_path,verbose = True)
    except Exception as e:
        print("Could not load real sensor: ",e)

    try:
        print("Loading simulated sensor...")
        sensor = fakesensor(main_path = main_path,verbose = True)
    except Exception as e:
        print("Could not load fake sensor data: ",e)

