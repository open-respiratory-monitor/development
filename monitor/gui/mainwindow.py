#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May  3 17:36:10 2020


mainwindow.py

This is where the mainwindow of the GUI is defined


@author: nlourie
"""

from PyQt5 import uic, QtCore, QtGui, QtWidgets

import os
import sys

# add the wsp directory to the PATH
main_path = os.path.dirname(os.getcwd())
sys.path.insert(1, main_path)


# import custom modules
from sensor import sensor
from data_handler import data_handler

class MainWindow(QtWidgets.QMainWindow):

    """
    The class taking care for the main window.
    It is top-level with respect to other panes, menus, plots and
    monitors.
    """
    
    # this is a signal that sends fastdata from the mainloop to the slowloop
    newrequest = QtCore.pyqtSignal(object)

    def __init__(self, main_path, verbose = False,*args, **kwargs):

        """
        Initializes the main window for the MVM GUI. See below for subfunction setup description.
        """

        super(MainWindow, self).__init__(*args, **kwargs)
        #uic.loadUi('mainwindow.ui', self)  # Load the .ui file
        
        # run in verbose mode?
        self.verbose = verbose
        
        # define the top level main path
        self.main_path = main_path
        if self.verbose:
            print(f"main: main path = {self.main_path}")
        
        # define the slow and fast data classes that hold the data generated by the loops
        self.fastdata = data_handler.fast_data()
        self.slowdata = data_handler.slow_data()
            
        # Start up the fast loop (data acquisition)
        self.fast_loop = data_handler.fast_loop(main_path = self.main_path, verbose = self.verbose)
        self.fast_loop.start()
        self.fast_loop.newdata.connect(self.update_fast_data)
        
        # start up the slow loop (calculations)
        self.slow_loop = data_handler.slow_loop(main_path = self.main_path, verbose = self.verbose)
        self.slow_loop.start()
        self.slow_loop.newdata.connect(self.update_slow_data)
        self.slow_loop.newdata.connect(self.fast_loop.update_cal)
        self.slow_loop.request_fastdata.connect(self.slowloop_request)
        self.newrequest.connect(self.slowloop.update_fast_data)
        
    def update_fast_data(self,data):
        if self.verbose:
            print("main: received new data from fastloop!")
            print(f"main: dP = {data.dp[-1]}")
        self.fastdata = data
        
    def update_slow_data(self,data):
        if self.verbose:
            print("main: received new data from slowloop!")
        self.slowdata = data
        
    def slowloop_request(self):
        if self.verbose:
            print(f"main: received request for data from slowloop")
        self.newrequest.emit(self.fastdata)
        
        
        
        