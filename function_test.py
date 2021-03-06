#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  4 13:07:31 2020

@author: nlourie
"""

import numpy as np

import matplotlib.pyplot as plt
from scipy import interpolate

class thing():
    def __init__(self):
        self.a = np.array([])
    
    def add_point_to_a(self,new_point,maxlen):
        self.a = self.add_new_point(self.a,new_point,maxlen)
    
    def add_new_point(self,arr,new_point,maxlen):
        # adds a new data point to the array,
        # and keeps gets rid of the oldest point

        if len(arr) < maxlen:
            arr = np.append(arr,new_point)
        else:
            arr[:-1] = arr[1:]
            arr[-1] = new_point
        
        return arr

thing = thing()

print(thing.a)
for i in range(10):
    
    thing.add_point_to_a(i,maxlen = 5)
    print(thing.a)
    
    
x = np.array([1,2,3,4,5])
y = np.array([2,5,6,1,9])

z = np.array([0,1,2,3,4,5,6])

s = interpolate.interp1d(x,y,kind = 'linear',fill_value = 'extrapolate')

plt.figure()
plt.plot(x,y,'ko')
plt.plot(z,s(z),'r-')