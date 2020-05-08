#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  8 13:21:32 2020

reading saved data


@author: nlourie
"""
import numpy as np
import matplotlib.pyplot as plt

from scipy import signal
from scipy import interpolate
from scipy import misc

flowcal = np.loadtxt('Flow_Calibration.txt',delimiter = '\t',skiprows = 1)

def breath_detect_coarse(flow,fs,plotflag = False):
    """
    %% This function detects peaks of flow signal
    
    % Inputs:
    %           flow:       flow signal
    %           fs:         sampling frequency
    %           plotflag:   set to 1 to plot
    
    % Output:
    %           peak (location, amplitude)
    
    % Written in matlab by: Chinh Nguyen, PhD
    % Email: c.nguyen@neura.edu.au
    % Source: 
    
    % Updated on: 12 Nov 2015.
    % Ver: 1.0
    
    # Converted to python from Matlab by: Nate Lourie, PhD
    # Email: nlourie@mit.edu
    # Updated on: April, 2020
    
    """
    # detect peaks of flow signal
    minpeakwidth = fs*0.3
    peakdistance = fs*1.5
    #print('peakdistance = ',peakdistance)
    minPeak = 0.2 # flow threshold = 0.05 (L/s)
    minpeakprominence = 0.05
    
    peak_index, _  = signal.find_peaks(flow, 
                                    height = minPeak,
                                    distance = peakdistance,
                                    prominence = minpeakprominence,
                                    width = minpeakwidth)
    
    #print('found peaks at index = ',peak_index)
    return peak_index


def dp2flow(dp_cmh20):
    flow_sign = np.sign(dp_cmh20)
    flow = flow_sign*np.polyval(flowcal,np.abs(dp_cmh20))
    return flow


def calculate_breath_params(i_min,i,time, vol):
    if len(i_min)>=2:
        try:
            iee = i_min[-1]
            
            iis = i_min[-2]
            

            tee = time[iee] # last end expiratory time
            tis = time[iis] # start of innspiration
            vol_breath = vol[i_min[-2]:i_min[-1]]
            
            vol_breath = vol[i_min[-2]:i_min[-1]]
            vt = np.max(vol_breath)
            index_range = np.arange(i_min[-2],i_min[-1]+1)

            iie = index_range[np.argmax(vol[i_min[-2]:i_min[-1]])]
            
            #print(f'iis = {iis}, i[iis] = {i[iis]}')
            #print(f"iie = {iie}, i[iie] = {i[iie]}")
            #rint(f'iee = {iee}, i[iee] = {i[iee]}')
            tie = time[iie]        
    
        except Exception as e:
            print('breath param calc error:',e)
            iee = None
            iie = None
            iis = None
            tee = None
            tis = None
            tie = None
            vt = 0.0
    else:
        iee = None
        iie = None
        iis = None
        tee = None
        tis = None
        tie = None
        vt = 0.0
        
    return iis,iie,iee,tis,tie,tee,vt
    
    
    

time,p1,p2,dp_raw = np.loadtxt('1588972688_sensor_raw.txt',delimiter = '\t',skiprows = 1,unpack = True)

i_raw = np.arange(len(time))



i0 = 0
irange =  200

def run(i0,irange):
    if irange == 'end':
        imax = len(time)
    else:
        imax = i0+irange
    
    
    #plt.ion()
    i = i_raw[i0:imax]

    dp = dp_raw[i0:imax]
    dp_zero = np.mean(dp[np.abs(dp)<0.1])
    dp = dp-dp_zero

    flow = dp2flow(dp)
    
    t = time[i0:imax]
    ts_real = np.abs(np.mean(t[1:] - t[:-1]))
    fs = 1.0/ts_real
    vol_raw = np.cumsum(flow)/(fs*60.0)
    v_model = []
    try:
        i_min = breath_detect_coarse(-1.0*vol_raw,fs)
        
        #print(f'found minima at i = {i[i_min]}')
        if len(i_min) >= 2:
            #print('interpolating')
            v_model = interpolate.interp1d(i[i_min],vol_raw[i_min],kind = 'linear',fill_value = 'extrapolate')
            v_drift = v_model(i)
            
            
            
        else:
            v_drift = 0*vol_raw
    except Exception as e:
        print(e)
        v_drift = 0*vol_raw
        
    vol = vol_raw - v_drift
    

    
    iis,iie,iee,tis,tie,tee,vt = calculate_breath_params(i_min,i,t, vol)
    
    
    ax1.cla()
    ax2.cla()
    ax3.cla()
    ax4.cla()

    
    ax1.plot(i,dp)
    ax2.plot(i,flow)
    ax3.plot(i,vol_raw)
    ax3.plot(i,v_drift)
    ax3.plot(i[i_min],vol_raw[i_min],'o')
    ax4.plot(i,vol)
    try:
        #ax4.plot(i[(t> tis) & (t<tie)],vol[(t> tis) & (t<tie)],'s')
        print (f'VT = {vt}, i:e = 1:{int((tee-tie)/(tie-tis))},RR = {60.0/(tee-tis)} bpm')
        ax4.plot(i[iis],vol[iis],'go')
        ax4.plot(i[iie],vol[iie],'yo')
        ax4.plot(i[iee],vol[iee],'ro')
    except Exception as e:
        print('breath plot error: ',e)

    
    
    ax2.set_ylim([-100,100])
    ax4.set_ylim([-0.5,2.0])
    
    ax1.set_ylabel('dP [cm H2O]')
    ax2.set_ylabel('Flow [L/m]')
    ax3.set_ylabel('Raw VT [L]')
    ax4.set_ylabel('VT [L]')
    
    f.canvas.draw()
    return i[i_min],v_model,v_drift
    
plt.ion()
f, (ax1,ax2,ax3,ax4) = plt.subplots(4,1)   
plt.tight_layout()
try:
    for i0 in np.arange(i0,len(time)-irange):
        imin,v_model,v_drift = run(i0,irange)
        plt.pause(0.01)
except KeyboardInterrupt:
    pass
