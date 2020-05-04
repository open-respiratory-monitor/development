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


# add the main directory to the PATH
main_path = os.path.dirname(os.getcwd())
sys.path.insert(1, main_path)

def main():
    """
    Main function.
    """

    app = QtWidgets.QApplication(sys.argv)

    window = mainwindow.MainWindow(main_path = main_path)
    window.show()
    app.exec_()



if __name__ == "__main__":
    main()
