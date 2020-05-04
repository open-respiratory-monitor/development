#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  4 13:07:31 2020

@author: nlourie
"""

import numpy as np

class thing():
    def __init__(self):
        self.a = np.array([])
    
    def add_point_to_a(self,new_point,maxlen):
        self.a = self.add_new_point(self.a,new_point,maxlen)
    
    def add_new_point(self,arr,new_point,maxlen):
        # adds a new data point to the array,
        # and keeps gets rid of the oldest point
        
        #throw away everything except the last maxlen points
    
        if len(arr) < maxlen:
            #print("length okay, just stick on value")
            arr = np.append(arr,new_point)
            #print("inside loop: arr = ",arr)
        else:
            #print("hit length limit, trim array")
            arr[:-1] = arr[1:]
            arr[-1] = new_point
            #print("inside loop: arr = ",arr)
        
        return arr

thing = thing()

print(thing.a)
for i in range(10):
    
    thing.add_point_to_a(i,maxlen = 5)
    print(thing.a)