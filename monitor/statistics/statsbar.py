#!/usr/bin/env python3
"""
Main window helper
"""
from PyQt5 import QtWidgets, uic



class statsbar(QtWidgets.QWidget):
    """
    Main window class
    """

        
    def __init__(self, parent=None):
        super(statsbar, self).__init__(parent)
        uic.loadUi('statistics/statsbar.ui', self)