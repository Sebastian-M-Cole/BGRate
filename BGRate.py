#!/usr/bin/python

# Written by Sebastian Cole 11/01/2017

# Methods to obtain the BGRate from RCDB conditions and user defined inputs. 
# All user defined inputs have default values. Running from a command line
# will produce a csv containing run_number, event_count, beam_on_current, 
# beam_energy, coherent_peak, collimator_diameter, and radiator_type obtained
# from the RCDB and BGRate obtained from the Hall D Coherent Bremsstrahlung rate
# calculator. 

# RCDB access requires correct path to RCDB_HOME and RCDB_HOME/python.
# This information can be found at the link below:
# https://github.com/JeffersonLab/rcdb/wiki/Installation#setup-environment-manually

# BGRate.py --help will produce a man page for the command line.

# MCWrapper can make use of BGRate_RCDB_values then CalcBGRate with the 
# constructed table on a run by run basis to produce the BGRate to be 
# used in the MC. 

# It will also make use of Richard Jones' code to calculate the BGRate
# which is written in C++ wrapped using boost to seemlessly implement
# in python. The work below will assist in ensuring the implementation
# of cobrems is functioning correctly. 

import argparse

parser = argparse.ArgumentParser(description='Obtain BGRate values using RCDB inputs to build run specific MC')
parser.add_argument('-p',action='store',dest='pathToRCDB',help='Path to rcdb.sqlite')
parser.add_argument('--minRun',action='store',dest='minRun',help='Min run number')
parser.add_argument('--maxRun',action='store',dest='maxRun',help='Max run number')
parser.add_argument('--beamEmittance',action='store',default=10e-09,dest='beamEmittance',help='Electronbeam emittance: default = 10e-09 m.')
parser.add_argument('--photonNbins',action='store',default=2000,dest='photonNbins',help='Number of bins in photon spectrum: default = 2000 bins.')
parser.add_argument('--photonEmax',action='store',default=12,dest='photonEmax',help='Photon spectrum energy maximum: default = 12 GeV.')
parser.add_argument('--photonEmin',action='store',default=3,dest='photonEmin',help='Photon spectrum energy minimum: default = 3 GeV.')
parser.add_argument('--collimDistance',action='store',default=76,dest='collimDistance',help='Radiator-collimator distance: default = 76 m.')
parser.add_argument('--peakElow',action='store',default=8.4,dest='peakElow',help='Low edge of primary window: default = 8.4 GeV.')
parser.add_argument('--peakEhigh',action='store',default=9,dest='peakEhigh',help='High edge of primary window: default = 9 GeV.')
parser.add_argument('--backElow',action='store',default=0.1,dest='backElow',help='Low edge of background window: default = 0.1 GeV.')
parser.add_argument('--backEhigh',action='store',default=3,dest='backEhigh',help='High edge of background window: default = 3 GeV.')
parser.add_argument('--endpElow',action='store',default=10,dest='endpElow',help='Low edge of endpoint tagging window: default = 10 GeV.')
parser.add_argument('--endpEhigh',action='store',default=11.7,dest='endpEhigh',help='High edge of endpoint tagging window: default = 11.7 GeV.')

parsedArgs = parser.parse_args()

from re import search
from urllib2 import urlopen
from os import environ
from sys import path
import rcdb

# Function that obtains the conditions from the RCDB for calculating 
# the BGRate using the Hall D Coherent Bremsstrahlung rate calculator.

def BGRate_RCDB_values(minRun,maxRun):
    #RCDB condition list
    valueList = ['event_count','beam_on_current','beam_energy','coherent_peak','collimator_diameter','radiator_type']

    db = rcdb.RCDBProvider("sqlite:///"+parsedArgs.pathToRCDB)
    table = db.select_runs("@is_production and @status_approved",int(minRun),int(maxRun)).get_values(valueList,True)

    return table # Table of conditions from list for 
                 # only production and status approved runs.

# Function that obtains the BGRate from input values from the RCDB and 
# user defined inputs. All user defined inputs have default values.

def CalcBGRate(table,beamEmittance=10e-09,photonNbins=2000,photonEmax=12.0,photonEmin=3.0,collimDistance=76.0,peakElow=8.4,peakEhigh=9,backElow=0.1,backEhigh=3.0,endpElow=10.0,endpEhigh=11.7):
    beamEmittanceStr  = '&beamEmittance=%g'%beamEmittance
    photonNbinsStr    = '&photonNbins=%i'%photonNbins
    photonEmaxStr     = '&photonEmax=%g'%photonEmax
    photonEminStr     = '&photonEmin=%g'%photonEmin
    collimDistanceStr = '&collimDistance=%g'%collimDistance
    peakElowStr       = '&peakElow=%g'%peakElow
    peakEhighStr      = '&peakEhigh=%g'%peakEhigh
    backElowStr       = '&backElow=%g'%backElow
    backEhighStr      = '&backEhigh=%g'%backEhigh
    endpElowStr       = '&endpElow=%g'%endpElow
    endpEhighStr      = '&endpEhigh=%g'%endpEhigh
    finalStr          = '&run=plot+collimated+beam+rate+spectrum'

    bc = table[2]*10**(-3)
    beamCurrentStr    = '&beamCurrent=%g'%bc
    be = table[3]*10**(-3)
    beamEnergyStr     = '&beamEnergy=%g'%be
    ep = table[4]*10**(-3)
    photonEpeakStr    = '&photonEpeak=%g'%ep
    cd = float(table[5].rstrip('mm hole'))*10**(-3)
    collimDiamStr     = '&collimDiam=%g'%cd
    rt = float(search('[A-Za-z0-9-]+ ([0-9]+)',table[6]).group(1))*10**(-6)
    radThicknessStr   = '&radThickness=%g'%rt

    webAddr = 'http://zeus.phys.uconn.edu/halld/cobrems/ratetool.cgi'

    conditions = '?' + beamEnergyStr + beamCurrentStr + beamEmittanceStr + radThicknessStr + photonEpeakStr + photonNbinsStr + photonEmaxStr + photonEminStr + collimDistanceStr + collimDiamStr + peakElowStr + peakEhighStr + backElowStr + backEhighStr + endpElowStr + endpEhighStr + finalStr

    CBRC_page = urlopen(webAddr+conditions).read()
    BGRate = search('<tr><td><b> Endpoint tagged flux sum is ([0-9.E+-]+)',CBRC_page).group(1)

    return float(BGRate)*10**(-9) # Endpoint tagged flux sum as determined using 
                                 # the Hall D Coherent Bremsstrahlung rate calculator.


# Constructs condition csv with run_number, event_count, beam_on_current, 
# beam_energy, coherent_peak, collimator_diameter, radiator_type, and BGRate

fileName = 'BGRateRCDBValue_%s-%s.csv'%(parsedArgs.minRun,parsedArgs.maxRun)
with open(fileName,'w') as f:
    f.write('run_number,event_count,beam_on_current,beam_energy,coherent_peak,collimator_diameter,radiator_type,BGRate\n')
    for run in BGRate_RCDB_values(parsedArgs.minRun,parsedArgs.maxRun):
        BGRate = CalcBGRate(run,parsedArgs.beamEmittance,parsedArgs.photonNbins,parsedArgs.photonEmax,parsedArgs.photonEmin,parsedArgs.collimDistance,parsedArgs.peakElow,parsedArgs.peakEhigh,parsedArgs.backElow,parsedArgs.backEhigh,parsedArgs.endpElow,parsedArgs.endpEhigh)
        runToWrite = ''
        for val in run:
            runToWrite += str(val) + ','
        f.write(runToWrite+'%g'%BGRate+'\n')


