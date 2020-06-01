"""
Alarm facility.
"""

import os
import sys

# add the wsp directory to the PATH
main_path = os.path.dirname(os.getcwd())
sys.path.insert(1, main_path)

# import custom modules

from utils import utils


from copy import copy
from audio import audio

class GuiAlarms:
    """
    This class checks whether observables are within allowed ranges. If out of range:
    1) The monitor displaying this observable is set into an alarm state
    2) We tell the ESP about the alarm condition.

    Class members:
    - _obs: {str: dict} for alarm settings, keyed by section name in the config file.
        See below for more details about dict keys.
    - _esp32: ESP32Serial object for communication
    - _monitors: {str: gui.monitor.Monitor}, keyed by monitor name
    - _start_stop_worker: gui.start_stop_worker.StartStopWorker
    - _mon_to_obs: {str: str} for monitor name -> observable name
    - _alarmed_monitors: set of monitor names that are currently in alarm state

    Keys for the settings in self._obs:
    - min: Minimum value that can be set for setmin/setmax
    - max: Maximum value that can be set for setmin/setmax
    - setmin: Alarm if value below this (if None - no lower bound)
    - setmax: Alarm if value above this  (if None - no upper bound)
    - linked_monitor: Name of the monitor connected to this observable
    - observable: Name of this observable
    - under_threshold_code: Not implemented yet
    - over_threshold_code: Not implemented yet
    """
    def __init__(self, config, monitors):
        """
        Constructor

        Arguments: see relevant class members.
        """
        self._obs = copy(config["alarms"])
        #self._esp32 = esp32
        self._monitors = monitors
        self._armed = False
        self._audio_armed = True
        self._mon_to_obs = {}
        
        self._audio_alarm = audio.audio_alarm(filepath = main_path + '/monitor/audio')

        for obs_name, settings in self._obs.items():
            print('guialarms: adding new alarm: ',obs_name)
            self._mon_to_obs[settings['linked_monitor']] = obs_name
            settings['min'] = settings.get('min', None)
            settings['max'] = settings.get('max', None)
            settings['setmin'] = settings.get('setmin', settings.get('min'))
            settings['setmax'] = settings.get('setmax', settings.get('max'))

        self._alarmed_monitors = set()
        self.update_mon_thresholds()

    
    def update_mon_thresholds(self):
        """
        Send the thresholds to the monitors
        """
        for settings in self._obs.values():
            try:
                monitor = self._monitors[settings['linked_monitor']]
                monitor.update_thresholds(settings.get('min'),
                                          settings.get('setmin'),
                                          settings.get('max'),
                                          settings.get('setmax'))
            except Exception as e:
                print(f'could not update threshold for monitor [{monitor}]: ',e)

    def _get_by_observable(self, observable):
        """
        Gets the dict configuration for a particular observable.

        Arguments:
        - observable: string

        Returns:
        dict, or None if observable not found
        """
        for settings in self._obs.values():
            if settings['observable'] == observable:
                return settings

        return None

    def _test_over_threshold(self, item, value):
        """
        If the current value is above configured max threshold, set the monitor
        into an alarmed state.

        Does nothing if there is no upper threshold defined.

        Arguments:
        - item: dict of settings from the config file
        - value: value to test against
        """
        
        
        if item['setmax'] is not None:
            if value > item["setmax"]:
                #self._esp32.raise_gui_alarm()
                linked_monitor = self._monitors[item['linked_monitor']]
                linked_monitor.set_alarm_state(isalarm=True)
                self._alarmed_monitors.add(linked_monitor.configname)
                print(f"GUI ALARM: {item['linked_monitor']} OVER THRESHOLD")

    def _test_under_threshold(self, item, value):
        """
        If the current value is below configured min threshold, set the monitor
        into an alarmed state.

        Does nothing if there is no upper threshold defined.

        Arguments:
        - item: dict of settings from the config file
        - value: value to test against
        """
        if item['setmin'] is not None:
            if value < item["setmin"]:
                #self._esp32.raise_gui_alarm()
                linked_monitor = self._monitors[item['linked_monitor']]
                linked_monitor.set_alarm_state(isalarm=True)
                self._alarmed_monitors.add(linked_monitor.configname)
                print(f"GUI ALARM: {item['linked_monitor']} UNDER THRESHOLD")

    def _test_thresholds(self, item, value):
        """
        If ventilation is currently happening, check if any monitors need
        to be put into an alarm state.

        Arguments:
        - item: dict of settings from the config file
        - value: value to test against
        """
        #print('guialarm: testing thresholds')
        if self._armed:
            self._test_over_threshold(item, value)
            self._test_under_threshold(item, value)

    def clear_alarm(self, name):
        """
        User has cleared the alarm state of a monitor. If all monitors are now okay,
        we will stop telling the ESP that there is an alarm.

        Arguments:
        - name: Monitor name
        """

        if name in self._alarmed_monitors:
            self._alarmed_monitors.remove(name)
            if len(self._alarmed_monitors) == 0:
                #self._esp32.snooze_gui_alarm()
                pass

        # self._esp32.reset_alarms()
        #obs = self._mon_to_obs.get(name, None)
        # if obs is not None:
        #    under_code = self._obs[obs]['under_threshold_code']
        #    over_code = self._obs[obs]['over_threshold_code']
        #    if under_code is not None:
        #        self._esp32.snooze_hw_alarm(under_code)
        #    if over_code is not None:
        #        self._esp32.snooze_hw_alarm(over_code)

    def set_data(self, data):
        """
        Check new observable values against thresholds.

        Arguments:
        - data: dict values, keyed by observable name.
        """
        #print(f'GUI ALARM: there are [{len(self._alarmed_monitors)}] alarmed monitors: ',self._alarmed_monitors)
        # sound audio alarm if there are any alarmed monitors
        
        if self._armed:
            
            # if there are no alarms, reset audio to default to sound when new alarms come in
            if len(self._alarmed_monitors) == 0:
                self._audio_armed = True
            
            if self._audio_armed:
                self.sound_alarms()
            
            for observable in data:
                item = self._get_by_observable(observable)
                if item is not None:
                    self._test_thresholds(item, data[observable])
        
        else:
            pass
    
    def sound_alarms(self):
        
        try:
            #print('GUI ALARM: sounding alarm if there are any alarms')
            if len(self._alarmed_monitors)>0:
                self._audio_alarm.sound_continuous()
            elif len(self._alarmed_monitors) == 0:
                self._audio_alarm.silence()
        except Exception as e:
            print('GUI ALARM: Could not sound audio alarm: ',e)
        
    def has_valid_minmax(self, name):
        """
        Check if max and min are not None.

        Arguments:
        - name: monitor name

        Returns: bool
        """
        obs = self._mon_to_obs.get(name, None)
        if obs is None:
            return False
        value_max = self._obs[obs]['max']
        value_min = self._obs[obs]['min']
        return value_max is not None and value_min is not None

    def get_setmin(self, name):
        """
        Get the lower alarm threshold.

        Arguments:
        - name: monitor name

        Returns: threshold, or False if no lower threshold set.
        """
        obs = self._mon_to_obs.get(name, None)
        if obs is None:
            return False

        return self._obs[obs].get('setmin', self._obs[obs]['min'])

    def get_setmax(self, name):
        """
        Get the upper alarm threshold.

        Arguments:
        - name: monitor name

        Returns: threshold, or False if observable is not known.
        """
        obs = self._mon_to_obs.get(name, None)
        if obs is None:
            return False

        return self._obs[obs].get('setmax', self._obs[obs]['max'])

    def get_min(self, name):
        """
        Get the minimum value that alarm threshold can be set to.

        Arguments:
        - name: monitor name

        Returns: lower limit, or False if observable is not known.
        """
        obs = self._mon_to_obs.get(name, None)
        if obs is None:
            return False

        return self._obs[obs]['min']

    def get_max(self, name):
        """
        Get the maximum value that alarm threshold can be set to.

        Arguments:
        - name: monitor name

        Returns: upper limit, or False if observable is not known.
        """
        obs = self._mon_to_obs.get(name, None)
        if obs is None:
            return False

        return self._obs[obs]['max']

    def update_min(self, name, minvalue):
        """
        Set the lower alarm threshold.

        Arguments:
        - name: monitor name
        - minvalue: lower threshold
        """
        obs = self._mon_to_obs.get(name, None)
        if obs is not None:
            self._obs[obs]['setmin'] = minvalue
            self.update_mon_thresholds()

    def update_max(self, name, maxvalue):
        """
        Set the upper alarm threshold.

        Arguments:
        - name: monitor name
        - minvalue: lower threshold
        """
        obs = self._mon_to_obs.get(name, None)
        if obs is not None:
            self._obs[obs]['setmax'] = maxvalue
            self.update_mon_thresholds()
    
    
    def arm_alarms(self):
        """
        arm the alarm handler
        """
        self._armed = True
        
    def disarm_alarms(self):
        """
        disarm the gui alarm handler
        """
        self._armed = False
        
        
        
        
        for monitor in self._monitors.values():
            #print('clearing observable: ',monitor['name'])
            
            monitor.set_alarm_state(isalarm=False)
            
        self._alarmed_monitors = set() 
        
     
    def silence_alarms(self):
        '''
        mute the audio alarms.
        '''
        self._audio_armed = False
        self._audio_alarm.silence()

if __name__ == '__main__':
    audio_alarm = audio.audio_alarm(filepath = main_path + '/audio/')