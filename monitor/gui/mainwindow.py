#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May  3 17:36:10 2020


mainwindow.py

This is where the mainwindow of the GUI is defined


@author: nlourie
"""

from PyQt5 import QtWidgets, uic

import os
import sys

# add the wsp directory to the PATH
main_path = os.path.dirname(os.getcwd())
sys.path.insert(1, main_path)

# import custom modules
from sensor import sensor
from data_handler import data_handler

class MainWindow(QtWidgets.QMainWindow):
    #pylint: disable=too-many-public-methods
    #pylint: disable=too-many-instance-attributes
    """
    The class taking care for the main window.
    It is top-level with respect to other panes, menus, plots and
    monitors.
    """

    def __init__(self, *args, **kwargs):

        """
        Initializes the main window for the MVM GUI. See below for subfunction setup description.
        """

        super(MainWindow, self).__init__(*args, **kwargs)
        #uic.loadUi('mainwindow.ui', self)  # Load the .ui file
          
        
        # Start up the fast loop (data acquisition)
        self.fast_loop = data_handler.fast_loop()
        self.fast_loop.start()
        self.fast_loop.newdata.connect(self.update_fast_data)
        
    def update_fast_data(self,data):
        print("Received New Data from Fast Loop!")
        print(data)