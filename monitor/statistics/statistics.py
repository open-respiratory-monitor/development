#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  2 12:55:04 2020

@author: nlourie
"""

import numpy as np

def add_new_point(arr,new_point,maxlen):
       # adds a new data point to the array,
       # and keeps gets rid of the oldest point

       if len(arr) < maxlen:
           arr = np.append(arr,new_point)
       else:
           arr[:-1] = arr[1:]
           arr[-1] = new_point

       return arr


class Stats():
    """
    this calculates and stores the statistics on an array
    """
    
    def __init__(self,array = np.array([])):
        
        self.data = array 
        self.update_stats()
    
    def update_stats(self):
           
        
        self.n_points = len(self.data)
        if self.n_points == 0:
            self.stderr = np.nan
            self.pcterr = np.nan
            self.mean = np.nan
            self.min = np.nan
            self.max = np.nan
            
        else:
            
            self.stderr = np.std(self.data)/np.sqrt(self.n_points)
            self.pcterr = 100.0*(self.stderr/self.mean)
            self.min = np.min(self.data)
            self.max = np.max(self.data)
            self.mean = np.mean(self.data)
        
        
class Statset():
    
    """
    this class holds a dictionary of statistics for the tracked varibles.
    """
    
    def __init__(self):
        self.names = []
        self.stats = dict()
        
    def add_stat(self,name):
        self.names.append(name)
        
        # create a new Stats instance
        stat = Stats()
        self.stats.update({name : stat})
    
    def add_data_point(self,name,data_point):
        self.stats[name].data = add_new_point(self.stats[name].data, data_point, 10)
        self.stats[name].update_stats()
        #print(f'stats: stat[{name}].data = {self.stats[name].data}')
    
    def reset_all(self):
        """
        empties all the previous data but keeps the structures
        """
        print('stats: clearing stats')
        for name in self.names:            
            self.stats[name].data = []
            self.stats[name].update_stats()