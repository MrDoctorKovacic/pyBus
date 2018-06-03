#!/usr/bin/python

import os
import sys
import time
import json
import signal
import random
import logging
import traceback

import pyBus_tickUtil as pB_ticker # Ticker for signals requiring intervals
import pyBus_bluetooth as pB_bt # For bluetooth audio controls

# This module will read a packet, match it against the json object 'DIRECTIVES' below. 
# The packet is checked by matching the source value in packet (i.e. where the packet came from) to a key in the object if possible
# Then matching the Destination if possible
# The joining the 'data' component of the packet and matching that if possible.
# The resulting value will be the name of a function to pass the packet to for processing of sorts.

#####################################
# GLOBALS
#####################################
# directives list - maps function to src:dest:data
# first level of directives is filtering the src, so put in the integer representation of the src
# second level is destination
# third level is data : function name
DIRECTIVES = {
  '44' : {
    'BF' : {
      '7401FF' : 'd_keyOut',
      '7400FF' : 'd_keyIn'
    }
  },
  '50' : {
    '68' : {
      '3210' : 'd_volumeDown',
      '3211' : 'd_volumeUp',
      '3B01' : 'd_steeringNext',
      '3B21' : 'd_steeringNext',
      '3B08' : 'd_steeringPrev',
      '3B28' : 'd_steeringPrev'
    },
    'C8' : {
      '01' : 'd_cdPollResponse', # This can happen via RT button or ignition
      '3B40' : 'd_RESET',
      '3BA0' : 'd_steeringSpeak'
    }
  },
  '80' : {
    'BF' : {
      'ALL' : 'd_custom_IKE' # Use ALL to send all data to a particular function
    }
  },
  #C0 06 68 31 00 00 0B 94 for mode button?
  '68' : {
    '18' : {
      '01'     : 'd_cdPollResponse',
      '380000' : '', # d_cdSendStatus
      '380100' : '',
      '380300' : '',
      '380A00' : 'd_cdNext',
      '380A01' : 'd_cdPrev',
      '380700' : '',
      '380701' : '',
      '380601' : '', # 1 pressed
      '380602' : 'd_togglePause', # 2 pressed
      '380603' : 'd_testSpeed', # 3 pressed
      '380604' : '', # 4 pressed
      '380605' : 'd_update', # 5 pressed
      '380606' : 'd_RESET', # 6 pressed
      '380400' : '', # prev Playlist function?
      '380401' : '', # next Playlist function?
      '380800' : '',
      '380801' : ''
    }
  },
  '9C' : {
    'BF' : {
      '7C0072' : '', # Convertible top down is pressed ['9C', '05', 'BF', ['7C', '00', '72'], '28']
      '7C0071' : '' # Convertible top up is pressed ['9C', '05', 'BF', ['7C', '00', '71'], '2B']
    }
  }
}

WRITER = None
SESSION_DATA = {}
TICK = 0.02 # sleep interval in seconds used between iBUS reads
AIRPLAY = False
TARGET_SIS_MAC    = "" # Target MAC address for a sister pi to recieve some data

#####################################
# FUNCTIONS
#####################################
# Set the WRITER object (the iBus interface class) to an instance passed in from the CORE module
def init(writer):
  global WRITER, SESSION_DATA
  WRITER = writer

  pB_ticker.init(WRITER)
  
  # Init scanning for bluetooth every so often
  pB_ticker.enableFunc("scanBluetooth", 20)

  SESSION_DATA["DOOR_LOCKED"] = False
  SESSION_DATA["POWER_STATE"] = False # TODO: to be toggled on key-in/key-out (distinguish between AUX/full power for power saving considerations)

  #pB_display.immediateText('PyBus Up')
  WRITER.writeBusPacket('3F', '00', ['0C', '4E', '01']) # Turn on the 'clown nose' for 3 seconds
  #3F 05 00 0C 4E 01 CK should be?

# Manage the packet, meaning traverse the JSON 'DIRECTIVES' object and attempt to determine a suitable function to pass the packet to.
def manage(packet):
  src = packet['src']
  dst = packet['dst']
  dataString = ''.join(packet['dat'])
  methodName = None

  try:
    dstDir = DIRECTIVES[src][dst]
    if ('ALL'  in dstDir.keys()):
      methodName = dstDir['ALL']
    else:
      methodName = dstDir[dataString]
  except Exception, e:
    logging.debug("Exception from packet manager [%s]" % e)
    
  result = None
  if methodName != None:
    methodToCall = globals().get(methodName, None)
    if methodToCall:
      logging.debug("Directive found for packet - %s" % methodName)
      try:
        result = methodToCall(packet)
      except:
        logging.error("Exception raised from [%s]" % methodName)
        logging.error(traceback.format_exc())
    
    else:
      logging.debug("Method (%s) does not exist" % methodName)
  else:
    logging.debug("MethodName (%s) does not match a function" % methodName)

  return result
  
def listen():
  global SESSION_DATA

  logging.info('Event listener initialized')
  while True:
    # Grab packet and manage appropriately
    packet = WRITER.readBusPacket()
    if packet:
      manage(packet)

    if SESSION_DATA["POWER_STATE"]: # if we are powered (and can assume router is online) push session data to socket
      SESSION_DATA["SESSION"] = True

    time.sleep(TICK) # sleep a bit

def shutDown():
  logging.debug("Killing tick utility")
  pB_ticker.shutDown()

class TriggerRestart(Exception):
  pass
class TriggerInit(Exception):
  pass

############################################################################
# FROM HERE ON ARE THE DIRECTIVES
# DIRECTIVES ARE WHAT I CALL SMALL FUNCTIONS WHICH ARE INVOKED WHEN A 
# CERTAIN CODE IS READ FROM THE IBUS.
#
# SO ADD YOUR OWN IF YOU LIKE, OR MODIFY WHATS THERE. 
# USE THE BIG JSON DICTIONARY AT THE TOP
############################################################################
# All directives should have a d_ prefix as we are searching GLOBALLY for function names.. so best have unique enough names
############################################################################
def d_keyOut(packet):
  global SESSION_DATA
  SESSION_DATA["POWER_STATE"] = False

def d_keyIn(packet):
  global SESSION_DATA
  SESSION_DATA["POWER_STATE"] = False
  
def d_update(packet):
  pass
  
def d_RESET(packet):
  pass

# This packet is used to parse all messages from the IKE (instrument control electronics), as it contains speed/RPM info. But the data for speed/rpm will vary, so it must be parsed via a method linked to 'ALL' data in the JSON DIRECTIVES
def d_custom_IKE(packet):
  packet_data = packet['dat']
  if packet_data[0] == '18':
    speed = int(packet_data[1], 16) * 2
    revs = int(packet_data[2], 16)

    sendState({'speed' : speed, 'revs' : revs}) 
    speedTrigger(speed) # This is a silly little thing for changing track based on speed)

def d_togglePause(packet):
  pB_bt.pause()

# NEXT command is invoked from the Radio. 
def d_cdNext(packet):
  pB_bt.nextTrack()

def d_cdPrev(packet):
  pB_bt.prevTrack()  

def d_steeringNext(packet):
  pB_bt.nextTrack()

def d_steeringPrev(packet):
  pB_bt.prevTrack()

def d_steeringSpeak(packet):
  pB_bt.pause()

# Respond to the Poll for changer alive
def d_cdPollResponse(packet):
  pB_ticker.disableFunc("announce") # stop announcing
  pB_ticker.disableFunc("pollResponse")
  pB_ticker.enableFunc("pollResponse", 30)

def d_testSpeed(packet):
  speedTrigger(110)

# Do whatever you like here regarding the speed!
def speedTrigger(speed):
  global SESSION_DATA
  pass

# Send state to sister Pi for long-term logging if turned on.
# TODO: Implement once bluetooth library is tested
def sendState(state):
  global TARGET_SIS_MAC
  logging.debug("Sending to sister pi state: [%s]", state)

  '''
  if(SESSION_DATA["POWER_STATE"]):
    pB_ticker.enableFunc("sendMessage", 1, 0, [TARGET_SIS_MAC, state]) # send non-blocking bluetooth message
  '''
      
################## DIRECTIVE UTILITY FUNCTIONS ##################
# Write current track to display 
def writeCurrentTrack():
  pass
  '''
  WRITER.writeBusPacket('18', '68', ['39', '02', '09', '00', '3F', '00', "Test", "Text"])
  '''

# Sets the text stack to something..
def _displayTrackInfo(text=True):
  pass
  '''
  infoQue = []
  textQue = []
  if text:
    textQue = _getTrackTextQue()
  infoQue = _getTrackInfoQue()
  pB_display.setQue(textQue + infoQue)
  '''

# Roll all 4 windows up
def _rollWindowsUp():
  WRITER.writeBusPacket('3F','00', ['0C', '53', '01']) # Put up window 1
  WRITER.writeBusPacket('3F','00', ['0C', '42', '01']) # Put up window 2
  WRITER.writeBusPacket('3F','00', ['0C', '55', '01']) # Put up window 3
  WRITER.writeBusPacket('3F','00', ['0C', '43', '01']) # Put up window 4

# Roll all 4 windows down
def _rollWindowsDown():
  WRITER.writeBusPacket('3F','00', ['0C', '52', '01']) # Put down window 1
  WRITER.writeBusPacket('3F','00', ['0C', '41', '01']) # Put down window 2
  WRITER.writeBusPacket('3F','00', ['0C', '54', '01']) # Put down window 3
  WRITER.writeBusPacket('3F','00', ['0C', '44', '01']) # Put down window 4

# Put Convertible Top Down
def _convertibleTopDown():
  WRITER.writeBusPacket('9C', 'BF', ['7C', '00', '72'])

# Put Convertible Top Up
def _convertibleTopUp():
  WRITER.writeBusPacket('9C', 'BF', ['7C', '00', '71'])

# Tell IKE to set the time
def _setTime(day, month, year, hour, minute):
  # Check inputs to make sure we don't break things:
  for c in [day, month, year, hour, minute]:
    if not isinstance(c, int) or c > 255 or c < 0:
      return False

  # Write Hours : Minutes
  WRITER.writeBusPacket('3B', '80', ['40', '01', ('{:02x}'.format(hour)).upper(), ('{:02x}'.format(minute)).upper()])
  # Write Day/Month/Year
  WRITER.writeBusPacket('3B', '80', ['40', '02', ('{:02x}'.format(day)).upper(), ('{:02x}'.format(month)).upper(), ('{:02x}'.format(year)).upper()])

  return True

#################################################################
