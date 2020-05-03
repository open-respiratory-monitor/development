#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May  3 17:35:15 2020


monitor.py

This is the top level monitor script for the open source respiratory monitor


@author: nlourie
"""

import sys
import os
import os.path
from PyQt5 import QtCore, QtWidgets


from gui import mainwindow

def main():
    """
    Main function.
    """

    app = QtWidgets.QApplication(sys.argv)

    window = mainwindow.MainWindow()
    window.show()
    app.exec_()



if __name__ == "__main__":
    main()
