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

def breath_detect_coarse(flow,fs,minpeak = 0.05,plotflag = False):
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
    minPeak = minpeak # flow threshold = 0.05 (L/s)
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

            iie = index_range[np.argmax(vol_breath)]
            
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
    
#%% 

#time,p1,p2,dp_raw = np.loadtxt('1588972688_sensor_raw.txt',delimiter = '\t',skiprows = 1,unpack = True)
time,p1,p2,dp_raw = np.loadtxt('Simulated_Data.txt',delimiter = '\t',skiprows = 1,unpack = True)
i_raw = np.arange(len(time))
ts = 0.01# sampling time

time = i_raw*ts



"""
i0 = 0
imax = i0+1000

i = i_raw[i0:imax]
dp = dp_raw[i0:imax]
flow = dp2flow(dp)
dp_t = 0.05
dp_zero = np.mean(dp[np.abs(dp)<dp_t])
flow_zero = dp2flow(dp_zero)

plt.figure()
plt.subplot(1,2,1)
plt.plot(i,dp)
plt.plot(i,0*i)
plt.plot(i,dp_t+0*i)
plt.plot(i,-dp_t+0*i)

plt.subplot(1,2,2)
plt.plot(i,flow)
plt.plot(i,flow-flow_zero)
plt.plot(i,0*i)

"""

#%%


i0 = 0

trange = 10 #seconds

irange =  int(trange/ts)

def run(i0,irange):
    if irange == 'end':
        imax = len(time)
    else:
        imax = i0+irange
    
    print('i0 = ',i0)
    #plt.ion()
    i = i_raw[i0:imax]
    p = p1[i0:imax]
    dp = dp_raw[i0:imax]
    dp_t = 0.05
    dp_zero = np.mean(dp[np.abs(dp)<dp_t])
    flow_zero = dp2flow(dp_zero)

    flow = dp2flow(dp)-flow_zero
    
    t = time[i0:imax]
    
    ts_real = np.abs(np.mean(t[1:] - t[:-1]))
    fs = 1.0/ts_real
    print(f"fs = {fs}")
    vol_raw = signal.detrend(np.cumsum(flow)/(fs*60.0))
    v_model = []
    try:
        i_min = breath_detect_coarse(-1.0*vol_raw,fs,minpeak = 0.05)
        print(f'found minima at i = {i[i_min]}')
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
    
    

    
    iis,iie,iee,tis,tie,tee,vt = calculate_breath_params(i_min,i,time, vol)
    
    t_meas = t[-1] - t[0]
    scale = 60.0/t_meas
    i_last_min = i[(t[-1] - t)<= t_meas]
    flow_min = flow[(t[-1] - t)<= t_meas]
    i_last_min_in = i_last_min[flow_min>0]
    flow_min_in = flow_min[flow_min>0]
    i_last_min_out = i_last_min[flow_min<0]
    flow_min_out = flow_min[flow_min<0]
    
    
    #flow_min = flow_min - flow_min[0]
    fs_min = fs*60.0
    mve_meas_in = np.abs(np.trapz(flow_min_in)/(fs_min) * scale)
    mve_meas_out = np.abs(np.trapz(flow_min_out)/(fs_min) * scale)
    mve_meas = np.mean([mve_meas_in,mve_meas_out])
    
    rr = np.round(60.0/(tee-tis),1)
    ie = np.round((tee-tie)/(tie-tis),1)
    mve_inf = rr * vt
    
    ax1.cla()
    ax2.cla()
    ax3.cla()
    ax4.cla()
    ax5.cla()
    
    
    #pmodel = interpolate.UnivariateSpline(i,p,s = 1)
    #ax5.plot(i,pmodel(i))
    #ax6.plot(i,misc.derivative(pmodel,x0 = i,n = 2,dx = 15/fs))
    try:
        #ax4.plot(i[(t> tis) & (t<tie)],vol[(t> tis) & (t<tie)],'s')
        print (f'VT = {vt}, i:e = 1:{ie},RR = {rr} bpm, mve_meas = {mve_meas}, mve_inf = {mve_inf}')
        ax5.plot(i[iis],vol[iis],'go')
        ax5.plot(i[iie],vol[iie],'yo')
        ax5.plot(i[iee],vol[iee],'ro')
        
        ax1.plot(i[iis],p[iis],'go')
        ax1.plot(i[iie],p[iie],'yo')
        ax1.plot(i[iee],p[iee],'ro')
    except Exception as e:
        print('breath plot error: ',e)

    
    
    #ax2.set_ylim([-200,200])
    #ax4.set_ylim([-0.1,1.5])
    #ax6.set_ylim([-10,10])
    
    ax1.set_ylabel('P [cm H2O]')
    ax2.set_ylabel('dP [L/m]')
    ax3.set_ylabel('Flow [L/m]')
    ax4.set_ylabel('Raw VT [L]')
    ax5.set_ylabel('VT')
    

    ax1.plot(i,p)
    ax2.plot(i,dp)
    ax3.plot(i,flow)
    ax3.plot(i_last_min_in,flow_min_in)
    ax3.plot(i_last_min_out,flow_min_out)

    ax4.plot(i,vol_raw)
    ax4.plot(i,v_drift)
    ax4.plot(i[i_min],vol_raw[i_min],'o')
    ax5.plot(i,vol)
    ax5.plot(i,0*vol)
    
    f.canvas.draw()
    return i[i_min],v_model,v_drift,vol_raw,p,flow,flow_min,t
    
plt.ion()
f, (ax1,ax2,ax3,ax4,ax5) = plt.subplots(5,1)   
plt.tight_layout()
try:
    for i0 in np.arange(0,len(time)-irange):
        imin,v_model,v_drift,vol_raw,p,flow,flow_min,t = run(i0,irange)
        plt.pause(0.001)
except KeyboardInterrupt:
    pass
