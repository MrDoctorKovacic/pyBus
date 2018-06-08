#!/usr/bin/python

import os
import sys
import time
import json
import signal
import random
import logging
import traceback
import datetime
import zmq

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
      #'3B21' : 'd_steeringNext',
      '3B08' : 'd_steeringPrev',
      #'3B28' : 'd_steeringPrev'
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


#####################################
# CONFIG
#####################################
TICK = 0.02 # sleep interval in seconds used between iBUS reads
AIRPLAY = False
LISTEN_SOCKET = 4884 # port that we listen on for external messages (from other networked pis)

#####################################
# Define Globals
#####################################
WRITER = None
SESSION_DATA = {}
SESSION_CONTEXT = None
SESSION_SOCKET = None

#####################################
# FUNCTIONS
#####################################
# Set the WRITER object (the iBus interface class) to an instance passed in from the CORE module
def init(writer):
  global WRITER, SESSION_DATA, SESSION_CONTEXT, SESSION_SOCKET

  # Start ibus writer
  WRITER = writer
  pB_ticker.init(WRITER)
  
  # Init scanning for bluetooth every so often
  #pB_ticker.enableFunc("scanBluetooth", 20)

  # Start context for inter-protocol communication
  SESSION_CONTEXT = zmq.Context()
  SESSION_SOCKET = SESSION_CONTEXT.socket(zmq.PUB)
  SESSION_SOCKET.bind("tcp://127.0.0.1:4884") 
  logging.info("Started ZMQ Socket at 4884")

  # Init session data (will be written to network)
  SESSION_DATA["DOOR_LOCKED"] = False
  SESSION_DATA["POWER_STATE"] = False # TODO: to be toggled on key-in/key-out (distinguish between AUX/full power for power saving considerations)
  SESSION_DATA["SPEED"] = 0
  SESSION_DATA["RPM"] = 0

  #pB_display.immediateText('PyBus Up')
  WRITER.writeBusPacket('3F', '00', ['0C', '4E', '01']) # Turn on the 'clown nose' for 3 seconds
  #3F 05 00 0C 4E 01 CK should be?

  # Set date/time. Redundant, but helps easily diagnose what time the Pi THINKS it is
  now = datetime.datetime.now()
  _setTime(now.day, now.month, now.year, now.hour, now.minute)

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

    # Check external messages
    message = checkExternalMessages()
    if message:
      manageExternalMessages(message)

    # Write to session state to file
    if SESSION_DATA["POWER_STATE"]: # if we are powered (and can assume router is online) push session data to socket
      SESSION_DATA["SESSION"] = True

      # Open file for writing session data
      session_file = open("/var/www/html/session.json","w")
      session_file.write(json.dumps(SESSION_DATA))
      session_file.close()

    time.sleep(TICK) # sleep a bit

# Handles various external messages, usually by calling an ibus directive
def manageExternalMessages(message):
  message_array = json.loads(message)

  # Directive / Bluetooth command verbatim
  if "directive" in message_array[0]:
    try:
      methodToCall = globals().get(message_array["directive"], None)
      data = methodToCall()

      # Either send (requested) data or an acknowledgement back to node
      if data is not None:
        response = json.dumps(data)
      else:
        response = "OK" # 10-4
      SESSION_SOCKET.send(response) 

    except Exception, e:
      logging.error("Failed to call directive from external command.\n{}".format(e))

# Checks for any external messages sent to socket,
def checkExternalMessages():
  global SESSION_SOCKET

  # Non-blocking, as to not interrupt parsing ibus messages
  try:
    message = SESSION_SOCKET.recv(flags=zmq.NOBLOCK)
    logging.debug("Got External Message: {}".format(message))
    return message

  # IF no messages are queued
  except zmq.Again:
    return None

def shutDown():
  logging.debug("Killing tick utility")
  pB_ticker.shutDown()

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

# This packet is used to parse all messages from the IKE (instrument control electronics), as it contains speed/RPM info. 
# But the data for speed/rpm will vary, so it must be parsed via a method linked to 'ALL' data in the JSON DIRECTIVES
def d_custom_IKE(packet):
  global SESSION_DATA
  packet_data = packet['dat']

  # IKE Speed / RPM Info
  if packet_data[0] == '18':
    speed = int(packet_data[1], 16) * 2
    revs = int(packet_data[2], 16)

    SESSION_DATA["SPEED"] = speed
    SESSION_DATA["REVS"] = revs
    speedTrigger(speed) # This is a silly little thing for changing track based on speed)
  
  # IKE Ignition Status
  elif packet_data[0] == '11':
    if (packet_data[1] == '00'): # Key Out. Should call d_keyOut or no?
      SESSION_DATA["POWER_STATE"] = False
    elif (packet_data[1] == '01'): # Pos 1
      SESSION_DATA["POWER_STATE"] = "POS_1"
    elif (packet_data[1] == '03'): # Pos 2
      SESSION_DATA["POWER_STATE"] = "POS_2"
    elif (packet_data[1] == '07'): # Start
      SESSION_DATA["POWER_STATE"] = "START"

  # IKE Temperature Status
  elif packet_data[0] == '19':
    SESSION_DATA["OUTSIDE_TEMP"] = packet_data[1]
    SESSION_DATA["COOLANT_TEMP"] = packet_data[2]

  # IKE OBC Estimated Range / Average Speed
  elif packet_data[0] == '24':
    if (packet_data[1] == '06'):
      SESSION_DATA["RANGE_KM"] = packet_data[3]+packet_data[4]+packet_data[5]+packet_data[6]
    elif (packet_data[1] == '0A'):
      SESSION_DATA["AVG_SPEED"] = packet_data[3]+packet_data[4]+packet_data[5]+packet_data[6]

def d_togglePause(packet):
  pB_bt.pause()

# NEXT command is invoked from the Radio. 
def d_cdNext(packet):
  pB_bt.nextTrack()

def d_cdPrev(packet):
  pB_bt.prevTrack()  

def d_steeringNext(packet):
  #pB_bt.nextTrack()
  _convertibleTopUp() # For testing

def d_steeringPrev(packet):
  #pB_bt.prevTrack()
  _convertibleTopDown() # For testing

def d_steeringSpeak(packet):
  pB_bt.pause()

# Respond to the Poll for changer alive
def d_cdPollResponse(packet):
  pass

def d_testSpeed(packet):
  speedTrigger(110)

# Do whatever you like here regarding the speed!
def speedTrigger(speed):
  global SESSION_DATA
  pass

################## DIRECTIVE UTILITY FUNCTIONS ##################

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
