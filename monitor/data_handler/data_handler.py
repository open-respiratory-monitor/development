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

# add the wsp directory to the PATH
main_path = os.path.dirname(os.getcwd())
sys.path.insert(1, main_path)

# import custom modules
from sensor import sensor


class fast_loop(QtCore.QThread):
    
    """
    This class gets and updates the data that gets plotted in realtime
    
    Needs to take a few things to get started:
        
        sensor -- an instance of the sensor class
    
    """
    
    
    def __init__(self,sensor):
        QtCore.QThread.__init__(self)
        #self.n = input("  Enter a number to count up to: ")
        self.index = 0
        self.dt = 1000

        
    def __del__(self):
        self.wait()
    
    def update(self):
        self.index +=1
        if (self.index % 2) == 0:
            #Then it's even
            print("1 Hz Loop: %d" % self.index)
    
        sensor.read()
        print (f" dP = {sensor.dp}")
    
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
