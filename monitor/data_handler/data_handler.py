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

# add the wsp directory to the PATH
main_path = os.path.dirname(os.getcwd())
sys.path.insert(1, main_path)

# import custom modules
from sensor import sensor

"""
# Define the fast and slow data objects that will be passed to the GUI thread
"""
class fast_data(object):
    def __init__(self):
        
        # pressures
        self.data.p1 = 0.0
        self.data.p2 = 0.0
        self.data.dp = 0.0
        
        # flow
        self.data.flow = 0.0
        
        # volume
        self.vol = 0.0
        
        # time
        self.time = datetime.utcnow()
        
        # pi GPIO state
        self.lowbatt = False
        self.charging = True
        
        


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
    
    def __init__(self):
        
        QtCore.QThread.__init__(self)
        #self.n = input("  Enter a number to count up to: ")
        self.index = 0
        self.dt = 1000
        
        # Define the instance of the object that will hold all the data
        self.data = fast_data()
        
        # Set up the sensor
        self.sensor = sensor.sensor()
        
    def __del__(self):
        self.wait()
    
    def update(self):
        self.index +=1
        
        # debugging: print an update of what we're doing
        if (self.index % 2) == 0:
            #Then it's even
            print("1 Hz Loop: %d" % self.index)
            
        # record the update time
        self.time = datetime.utcnow()
        
        # read the pressure sensor data
        self.sensor.read()
        self.data.p1 = self.sensor.p1
        self.data.p2 = self.sensor.p2
        self.data.dp = self.sensor.dp    
        
        # debugging: print the sensor dP
        print (f" dP = {self.sensor.dp}")
        
        # tell the newdata signal to emit every time we update the data
        self.newdata.emit(self.data)
    
    def run(self):
        print("Starting 1 Hz Loop")
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
    
    def __init__(self):
        QtCore.QThread.__init__(self)
        #self.n = input("  Enter a number to count up to: ")
        self.index = 0
    def __del__(self):
        self.wait()
    
    def update(self):
        self.index +=1
        if (self.index % 2) == 0:
            #Then it's even
            print("1 Hz Loop: %d" % self.index)
    
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
