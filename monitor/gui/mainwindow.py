#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May  3 17:36:10 2020


mainwindow.py

This is where the mainwindow of the GUI is defined


@author: nlourie
"""

from PyQt5 import uic, QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import os
import sys
import numpy as np

# add the wsp directory to the PATH
main_path = os.path.dirname(os.getcwd())
sys.path.insert(1, main_path)


# import custom modules
#from sensor import sensor
#from settings.settings import Settings
#from settings.settingsfile import SettingsFile
from data_handler import data_handler, data_filler
from frozenplots.frozenplots import Cursor
from monitor_class.Monitor import Monitor
#from messagebar.messagebar import MessageBar
#from numpad.numpad import NumPad
from alarms.guialarms import GuiAlarms
from alarm_handler import AlarmHandler

#from communication.fake_esp32serial import FakeESP32Serial
#from alarm_handler import AlarmHandler

#from start_stop_worker import StartStopWorker
#from utils import utils

class MainWindow(QtWidgets.QMainWindow):

    """
    The class taking care for the main window.
    It is top-level with respect to other panes, menus, plots and
    monitors.
    """

    # this is a signal that sends fastdata from the mainloop to the slowloop
    request_from_slowloop = QtCore.pyqtSignal(object)
    request_to_update_cal = QtCore.pyqtSignal(object)
    update_vol_offset = QtCore.pyqtSignal()

    def __init__(self,  config, main_path, mode = 'normal', diagnostic = False, verbose = False,simulation = False,logdata = False,*args, **kwargs):

        """
        Initializes the main window
        """

        super(MainWindow, self).__init__(*args, **kwargs)
        uic.loadUi('mainwindow.ui', self)  # Load the .ui file

        # set mode
        if mode.lower() == 'debug':
            self.fast_update_time = 100
            self.fslow_update_time = 1000
            self.mode_verbose = True

        else:
            self.fast_update_time = 10
            self.slow_update_time = 1000
            self.mode_verbose = False

        # configuration
        self.config = config

        # data filler
        self.data_filler = data_filler.DataFiller(config = self.config)

        # run in verbose mode? do this if requested specifically or if running in debug mode
        self.verbose = (verbose) or (self.mode_verbose)

        # define the top level main path
        self.main_path = main_path
        if self.verbose:
            print(f"main: main path = {self.main_path}")

        # define the slow and fast data classes that hold the data generated by the loops
        self.time_to_display = 10 #seconds
        self.num_samples = int(self.time_to_display*1000/self.fast_update_time )

        #hold an index about where in the plot (ie an index within num_samples) to put the next data
        self.index = 0

        self.fastdata = data_handler.fast_data()
        self.slowdata = data_handler.slow_data()

        # Start up the fast loop (data acquisition)
        self.fast_loop = data_handler.fast_loop(main_path = self.main_path, config = self.config, simulation = simulation, logdata = logdata,verbose = self.verbose)
        self.fast_loop.start()
        self.fast_loop.newdata.connect(self.update_fast_data)


        # start up the slow loop (calculations)
        self.slow_loop = data_handler.slow_loop(main_path = self.main_path, config = self.config,  verbose = self.verbose)
        self.slow_loop.start()
        self.slow_loop.newdata.connect(self.update_slow_data)

        # if the slowloop requests new data, send it the current fastdata
        self.slow_loop.request_fastdata.connect(self.slowloop_request)
        self.request_from_slowloop.connect(self.slow_loop.update_fast_data)

        # rezero the volume offset
        self.update_vol_offset.connect(self.fast_loop.update_vol_offset)

        # want to just show the plots to dewbug the calculations?
        self.diagnostic = diagnostic
        ### GUI stuff ###
        self.setWindowTitle("Open Respiratory Monitor")

        '''
        Get the toppane and child pages
        '''
        #self.toppane = self.findChild(QtWidgets.QStackedWidget, "toppane")
        self.main = self.findChild(QtWidgets.QWidget, "main")
        #self.initial = self.findChild(QtWidgets.QWidget, "initial")
        #self.startup = self.findChild(QtWidgets.QWidget, "startup")
        self.alarmbar = self.findChild(QtWidgets.QWidget, "alarmbar")

        
        '''
        Get the center pane (plots) widgets
        '''
        self.centerpane = self.findChild(
            QtWidgets.QStackedWidget, "centerpane")
        self.plots_all = self.findChild(QtWidgets.QWidget, "plots_all")



        self.plots = {}
        for name in self.config['plots']:
            plot = self.main.findChild(QtWidgets.QWidget, name)
            self.data_filler.connect_plot(name,plot)
            self.plots[name] = plot


        '''
        Get the alarm-related stuff
        '''
        self.alarms_settings = self.findChild(
            QtWidgets.QWidget, "alarms_settings")
        self.alarmsbar = self.findChild(QtWidgets.QWidget, "alarmsbar")




        '''
        Get the stackable bits on the right
        '''
        self.rightbar = self.main.findChild(
            QtWidgets.QStackedWidget, "rightbar")
        self.monitors_bar = self.main.findChild(
            QtWidgets.QWidget, "monitors_bar")
        self.frozen_right = self.main.findChild(
            QtWidgets.QWidget, "frozenplots_right")


        self.button_backalarms = self.alarmsbar.findChild(
            QtWidgets.QPushButton, "button_backalarms")
        self.button_applyalarm = self.alarmsbar.findChild(
            QtWidgets.QPushButton, "button_applyalarm")
        self.button_resetalarm = self.alarmsbar.findChild(
            QtWidgets.QPushButton, "button_resetalarm")
        self.button_upalarm = self.alarmsbar.findChild(
            QtWidgets.QPushButton, "button_upalarm")
        self.button_downalarm = self.alarmsbar.findChild(
            QtWidgets.QPushButton, "button_downalarm")
        self.button_offalarm = self.alarmsbar.findChild(
            QtWidgets.QPushButton, "button_offalarm")

        '''
        Get the bar at the bottom
        '''

        self.frozen_bot = self.findChild(
            QtWidgets.QWidget, "frozenplots_bottom")
        # Get frozen plots bottom bar widgets and connect
        self.button_unfreeze = self.frozen_bot.findChild(
            QtWidgets.QPushButton, "button_unfreeze")


        self.settingsfork = self.findChild(
            QtWidgets.QWidget, "settingsforkbar")
        self.button_alarms = self.settingsfork.findChild(
            QtWidgets.QWidget,"button_alarms")
        self.button_arm = self.settingsfork.findChild(
            QtWidgets.QWidget,"button_arm")
        self.button_freeze = self.settingsfork.findChild(
            QtWidgets.QWidget,"button_freeze")


        self.button_backalarms = self.alarmsbar.findChild(
            QtWidgets.QPushButton, "button_backalarms")
        self.button_applyalarm = self.alarmsbar.findChild(
            QtWidgets.QPushButton, "button_applyalarm")
        self.button_resetalarm = self.alarmsbar.findChild(
            QtWidgets.QPushButton, "button_resetalarm")
        self.button_upalarm = self.alarmsbar.findChild(
            QtWidgets.QPushButton, "button_upalarm")
        self.button_downalarm = self.alarmsbar.findChild(
            QtWidgets.QPushButton, "button_downalarm")
        self.button_offalarm = self.alarmsbar.findChild(
            QtWidgets.QPushButton, "button_offalarm")


        '''
        Frozen Plot menu
        '''

        # Connect the frozen plots
        # Requires building of an ordered array to associate the correct
        # controls with the plot.
        active_plots = []
        for slotname in self.plots:
            active_plots.append(self.plots[slotname])
        self.cursor = Cursor(active_plots)
        self.frozen_bot.connect_workers(
            self.data_filler, active_plots, self.cursor)
        self.frozen_right.connect_workers(active_plots, self.cursor)






        # Frozen Plots
        self.button_freeze.pressed.connect(self.freeze_plots)
        self.button_unfreeze.pressed.connect(self.unfreeze_plots)

        '''
        Define the monitors
        '''

        # The monitored fields from the default_settings.yaml config file
        self.monitors = {}
        for name in config['monitors']:
            monitor = Monitor(name, config)
            self.monitors[name] = monitor
            self.data_filler.connect_monitor(monitor)
        # Get displayed monitors
        self.monitors_slots = self.main.findChild(
            QtWidgets.QVBoxLayout, "monitors_slots")
        self.alarms_settings.connect_monitors(self)
        self.alarms_settings.populate_monitors()
        self.button_applyalarm.pressed.connect(
            self.alarms_settings.apply_selected)
        self.button_resetalarm.pressed.connect(
            self.alarms_settings.reset_selected)
        self.button_offalarm.pressed.connect(
            self.alarms_settings.move_selected_off)
        self.button_upalarm.pressed.connect(
            self.alarms_settings.move_selected_up)
        self.button_downalarm.pressed.connect(
            self.alarms_settings.move_selected_down)



        '''
        Connect the menu buttons to actions
        '''
        self.button_alarms.pressed.connect(self.goto_alarms)

        self.alarms_settings.connect_monitors(self)
        self.alarms_settings.populate_monitors()
        self.button_applyalarm.pressed.connect(
            self.alarms_settings.apply_selected)
        self.button_resetalarm.pressed.connect(
            self.alarms_settings.reset_selected)
        self.button_offalarm.pressed.connect(
            self.alarms_settings.move_selected_off)
        self.button_upalarm.pressed.connect(
            self.alarms_settings.move_selected_up)
        self.button_downalarm.pressed.connect(
            self.alarms_settings.move_selected_down)
        self.button_backalarms.pressed.connect(self.exit_alarms)


        '''
        Start the alarm handler, which will check for ESP alarms
        '''
        self.alarm_h = AlarmHandler(self.config, self.alarmbar)

        # The alarms are from the default_settings.yaml config file
        # self.alarms = {}
        # for name in config['alarms']:
        #     alarm = GuiAlarm(name, config, self.monitors, self.alarm_h)
        #     self.alarms[name] = alarm
        self.gui_alarm = GuiAlarms(config, self.monitors)

        print('trying to connect alarms')
        for monitor in self.monitors.values():
            monitor.connect_gui_alarm(self.gui_alarm)



        # Show the Page
        self.goto_main()
        self.show_settingsfork()

        ### Stuff from the original just plots gui ###
        if self.diagnostic:
            self.graph1 = pg.PlotWidget()
            self.graph2 = pg.PlotWidget()
            self.graph3 = pg.PlotWidget()

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.graph1)
            layout.addWidget(self.graph2)
            layout.addWidget(self.graph3)

            widget = QtWidgets.QWidget()
            widget.setLayout(layout)

            # make the window with a graph widget
            self.setCentralWidget(widget)

            # set the plot properties
            self.graph1.setBackground('k')
            self.graph1.showGrid(x = True, y = True)
            self.graph2.setBackground('k')
            self.graph2.showGrid(x = True, y = True)
            self.graph3.setBackground('k')
            self.graph3.showGrid(x = True, y = True)

            # Set the label properties with valid CSS commands -- https://groups.google.com/forum/#!topic/pyqtgraph/jS1Ju8R6PXk
            labelStyle = {'color': '#FFF', 'font-size': '12pt'}
            self.graph1.setLabel('left','P','cmH20',**labelStyle)
            self.graph2.setLabel('left','Flow','L/m',**labelStyle)
            self.graph3.setLabel('left','V','mL',**labelStyle)
            self.graph3.setLabel('bottom', 'Time', 's', **labelStyle)

            # change the plot range
            #self.graph1.setYRange(-10,40,padding = 0.1)
            #self.graph2.setYRange(-100,100,padding = 0.1)
            #self.graph3.setYRange(0,750,padding = 0.1)

            # make a QPen object to hold the marker properties
            yellow = pg.mkPen(color = 'y',width = 2)
            pink = pg.mkPen(color = 'm', width = 2)
            green = pg.mkPen(color = 'g', width = 2)

            # define the curves to plot
            self.data_line1 = self.graph1.plot(self.fastdata.dt,    self.fastdata.p1,       pen = yellow)
            #self.data_line1b = self.graph1.plot(self.fastdata.dt,   self.fastdata.p2, pen = bluepen)
            self.data_line2 = self.graph2.plot(self.fastdata.dt,    self.fastdata.dp, pen = pink)
            self.data_line3 = self.graph3.plot(self.fastdata.dt,    self.fastdata.vol*1000,      pen = green)




        # update the graphs at regular intervals (so it runs in a separate thread!!)
        # Stuff with the timer
        self.t_update = self.fast_update_time #update time of timer in ms
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.t_update)
        self.timer.timeout.connect(self.update_plots)
        self.timer.start()




    ### MVM gui-related functions ###
    def lock_screen(self):
        """
        Perform screen locking.
        """

        self.toppane.setDisabled(True)
        self.show_toolbar(locked_state=True)
        self.alarms_settings.set_enabled_state(False)

    def unlock_screen(self):
        """
        Perform screen unlocking.
        """

        self.toppane.setEnabled(True)
        self.show_toolbar(locked_state=False)
        self.alarms_settings.set_enabled_state(True)

    def handle_unlock(self):
        """
        Handle the screen unlock procedure.
        """

        button = self.button_unlockscreen
        if button.isDown():
            if button._state == 0:
                button._state = 1
                button.setAutoRepeatInterval(50)
            else:
                self.show_numpadbar()
                button._state = 0
                button.setAutoRepeatInterval(self.unlockscreen_interval)

    def goto_new_patient(self):
        """
        Go ahead with shallow set of operational parameters.
        """

        self.show_startup()

    def goto_resume_patient(self):
        """
        Go ahead with previously used operational parameters.
        """

        self.settings.update_config(self.user_settings)

        self.show_startup()

    def goto_settings(self):
        """
        Open the Settings pane.
        """

        self.show_settings()
        self.show_settingsbar()
        if self._start_stop_worker.mode() == self._start_stop_worker.MODE_PSV:
            self.settings.tabs.setCurrentWidget(self.settings.tab_psv)
        elif self._start_stop_worker.mode() == self._start_stop_worker.MODE_PCV:
            self.settings.tabs.setCurrentWidget(self.settings.tab_pcv)

    def goto_main(self):
        """
        Open the home ui
        """

        self.show_main()
        #self.show_toolbar()

    def exit_settings(self):
        """
        Go back to home ui from the Settings pane.
        """

        self.show_main()
        self.show_menu()

    def goto_alarms(self):
        """
        Open the alarms settings pane.
        """

        self.show_alarms()
        self.show_alarmsbar()
        self.alarms_settings.config_monitors()

    def exit_alarms(self):
        """
        Go back to home ui from the alarms settings pane.
        """

        self.show_main()
        self.show_plots()
        self.show_settingsfork()
        self.alarms_settings.deconfig_monitors()

    def show_settings(self):
        """
        Open the Settings pane.
        """

        self.toppane.setCurrentWidget(self.settings)
        self.settings.tabs.setFocus()

    def show_startup(self):
        """
        Show the startup pane.
        """

        self.toppane.setCurrentWidget(self.startup)

    def show_menu(self):
        """
        Open the menu on the bottom of the home pane.
        """

        self.bottombar.setCurrentWidget(self.menu)

    def show_numpadbar(self):
        """
        Shows the numeric pad in the bottom of the home pane.
        """
        self.bottombar.setCurrentWidget(self.numpadbar)

    def show_toolbar(self, locked_state=False):
        """
        Shows the toolbar in the bottom bar.

        arguments:
        - locked_state: If true, shows the unlock button. Otherwise
                        shows the menu button.
        """
        self.bottombar.setCurrentWidget(self.toolbar)
        if locked_state:
            self.home_button.setCurrentWidget(self.goto_unlock)
        else:
            self.home_button.setCurrentWidget(self.goto_menu)

    def show_settingsbar(self):
        """
        Open the settings submenu.
        """

        self.bottombar.setCurrentWidget(self.settingsbar)

    def show_specialbar(self):
        """
        Open the special operations submenu.
        """

        self.bottombar.setCurrentWidget(self.specialbar)

    def show_main(self):
        """
        Show the home pane.
        """

        self.toppane.setCurrentWidget(self.main)

    def show_settingsfork(self):
        """
        Show the intermediate settings submenu
        """

        self.bottombar.setCurrentWidget(self.settingsfork)

    def show_alarms(self):
        """
        Shows the alarm settings controls in the center of the alarm
        settings pane.
        """

        self.centerpane.setCurrentWidget(self.alarms_settings)

    def show_plots(self):
        """
        Shows the plots in the center of the home pane.
        """

        self.centerpane.setCurrentWidget(self.plots_all)

    def show_alarmsbar(self):
        """
        Shows the alarm settings controls in the bottom of the alarm
        settings pane.
        """

        self.bottombar.setCurrentWidget(self.alarmsbar)

    def freeze_plots(self):
        """
        Open the frozen plots pane.
        """

        self.data_filler.freeze()
        self.rightbar.setCurrentWidget(self.frozen_right)
        self.bottombar.setCurrentWidget(self.frozen_bot)

    def unfreeze_plots(self):
        """
        Go back to the home pane from the frozen plots pane.
        """

        self.data_filler.unfreeze()
        self.rightbar.setCurrentWidget(self.monitors_bar)
        self.show_main()
        self.show_settingsfork()

    ### gui-related functions
    def update_plots(self):


        # update the plots with the new data
        if self.diagnostic:
            self.data_line1.setData(self.fastdata.dt,   self.fastdata.p1)
            #self.data_line1b.setData(self.fastdata.dt,   self.fastdata.p2)
            self.data_line2.setData(self.fastdata.dt,   self.fastdata.flow)
            self.data_line3.setData(self.fastdata.dt,   self.fastdata.vol*1000) #update the data


        #
        else:
            for key in self.fastdata.all_fields.keys():
                self.data_filler.add_data_point(key,self.fastdata.all_fields[key])
            #check if the looping is restarting
            if self.data_filler._looping_restart:
                if True:
                    print('main: restarting loop on plots')
                self.update_vol_offset.emit()
                
    def update_monitors(self):
        """
        displayed_monitors:
        - peak
        - peep
        - minute_volume_measured
        - tidal_volume
        - respiratory_rate
        - i_to_e_ratio
        - cstat
        - apnea_time
        - battery_low
        - battery_charging

        self.monitor_mapping = {'peak' : self.slowdata.pip,
                       'peep' : self.slowdata.peep,
                       'minute_volume_measured' : self.slowdata.mve_meas,
                       'tidal_volume' : self.slowdata.vt,
                       'respiratory_rate': self.slowdata.rr,
                       'i_to_e_ratio' : self.slowdata.ie,
                       'cstat' : self.slowdata.c,
                       'apnea_time' : self.slowdata.dt_last,
                       'battery_low': self.slowdata.lowbatt,
                       'battery_charging' : self.slowdata.battery_charging}


        """
        self.monitor_mapping = {'peak' : self.slowdata.pip,
                       'peep' : self.slowdata.peep,
                       'minute_volume_measured' : self.slowdata.mve_meas,
                       'tidal_volume' : self.slowdata.vt,
                       'respiratory_rate': self.slowdata.rr,
                       'i_to_e_ratio' : self.slowdata.ie,
                       'cstat' : self.slowdata.c,
                       'apnea_time' : self.slowdata.dt_last,
                       'battery_low': self.slowdata.lowbatt,
                       'battery_charging' : self.slowdata.charging}




        for key in self.monitor_mapping.keys():
            try:
                value = self.monitor_mapping[key]
                if self.verbose:
                    print(f'main: adding to {key}: {value}')
                self.data_filler.add_data_point(key,value)

            except Exception as e:
                #print(f'main: could not update monitor {key}: ',e)
                pass
         
        # check for alarms
        """
        self.gui_alarm = GuiAlarms(config, self.monitors)

        print('trying to connect alarms')
        for monitor in self.monitors.values():
            monitor.connect_gui_alarm(self.gui_alarm)
        """
        
        try:
            self.gui_alarm.set_data(self.monitor_mapping)
        except Exception as e:
            print('main: could not send data to guialarm: ',e)
            
    ### slots to handle data transfer between threads ###
    def update_fast_data(self,data):
        if self.verbose:
            print("main: received new data from fastloop!")

        self.fastdata = data
        #self.update_plots()

    #def reset_volume_offset(self):
        #self.fastloop.

    
    def update_slow_data(self,data):
        if self.verbose:
            print("main: received new data from slowloop!")
        self.slowdata = data
        self.update_monitors()
        #os.system('cls' if os.name == 'nt' else 'clear')
        #data.print_data()

    def slowloop_request(self):
        if self.verbose:
            print(f"main: received request for data from slowloop")
        self.request_from_slowloop.emit(self.fastdata)