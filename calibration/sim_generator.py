#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 11 12:15:14 2020

Makes a set of test data pressures and flows based on the MVM test data


@author: nlourie
"""

import numpy as np
import matplotlib.pyplot as plt


flowcal = np.loadtxt('Flow_Calibration.txt',delimiter = '\t',skiprows = 1)

invflowcal = np.loadtxt('Inverse_Flow_Calibration.txt',delimiter = '\t',skiprows = 1)

def dp2flow(dp_cmh20):
    flow_sign = np.sign(dp_cmh20)
    flow = flow_sign*np.polyval(flowcal,np.abs(dp_cmh20))
    return flow


def flow2dp(flow_lpm):
    flow_sign = np.sign(flow_lpm)
    dp = flow_sign*np.polyval(invflowcal, np.abs(flow_lpm))
    return dp





dt = np.abs(0.342873-0.343789)
fs = 1/dt

mvmdata = np.loadtxt('MVM_TestData.txt',delimiter = '\t',skiprows = 4,unpack = True)


# create a time vector. the MVM data is sampled at 1k Hz (dt = 0.01 s)
n_samples = len(mvmdata[0])

time = np.linspace(0,(n_samples-1) * 0.001,num = n_samples)   

# get the relevant vectors:
mvm_p1 = mvmdata[2]
mvm_flow = mvmdata[5]

# resample pressures and flow so it works out to nicer tidal volumes with the 100 Hz sample rate
n = 3
p1 = mvm_p1[0::n]
mvm_flow = mvm_flow[0::n]
time = time[0::n] 

# now convert from flow into dp using the calibration from the spirometer
dp = flow2dp(mvm_flow)

# convert back into flow 
flow = dp2flow(dp)

# now infer the second pressure
p2 = dp + p1

data_out = np.column_stack((time, p1, p2, dp))
np.savetxt('Simulated_Data.txt',data_out,delimiter = '\t',header = 'Simulation data based on MVM Measurements: https://github.com/MechanicalVentilatorMilano/MVMAnalysis')

#%%
# Check that it's working
time,p1,p2,dp = np.loadtxt('Simulated_Data.txt',delimiter = '\t',skiprows = 1,unpack = True)
flow = dp2flow(dp)
 
# assume the sample rate of the monitor
dt = 10.0/1000
fs = 1.0/dt

vol_raw = np.cumsum(flow)/((100)*60.0)



# plot
plt.figure()
plt.subplot(5,1,1)
plt.plot(time,p1)
plt.ylabel('P1')

plt.subplot(5,1,2)
plt.plot(time,p2)
plt.ylabel('P2')

plt.subplot(5,1,3)
plt.plot(time,dp)
plt.ylabel('dP')

plt.subplot(5,1,4)
plt.plot(time,mvm_flow,label = 'MVM Flow')
plt.plot(time,flow,label = 'Inferred Flow')
plt.xlabel('time')
plt.ylabel('Flow from MVM')
plt.legend()

plt.subplot(5,1,5)
plt.plot(time,vol_raw)
plt.ylabel('Raw Volume')

plt.tight_layout()
