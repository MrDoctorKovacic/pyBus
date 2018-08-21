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
  '00' : {
    'BF' : {
      '0200B9' : 'd_carUnlocked', # Unlocked via key
      '7212DB' : 'd_carLocked', # Locked via key
      '7A1000' : None, # passenger door opened, probably
      '7A5202' : None, # passenger door closed, probably
      '7A5020' : None, # driver window popped up after closing door
      '7A5021' : None, # driver door closed
      '7A5120' : None, # driver window popped down before opening door
      '7A5121' : None, # driver door opened
    }
  },
  '3F' : {
    '00' : {
      '0C3401' : 'd_carUnlocked', # All doors unlocked
      '0C4601' : 'd_passengerDoorLocked',
      '0C4701' : 'd_driverDoorLocked',
    }
  },
  '44' : {
    'BF' : {
      '7401FF' : 'd_keyOut',
        '7400' : 'd_keyIn',
          '7A' : 'd_windowDoorMessage'
    }
  },
  '50' : { # MF Steering Wheel Buttons
    '68' : { # RADIO
      '3210' : 'd_volumeDown',
      '3211' : 'd_volumeUp',
      '3B01' : 'd_steeringNext',
      '3B11' : None, # Next, long press
      '3B21' : None, # Next Released
      '3B08' : 'd_steeringPrev',
      '3B18' : None, # Prev, long press
      '3B28' : None # Prev Released
    },
    'C8' : {
      '01' : None, # This can happen via RT button or ignition
      '019A' : None, # RT Button
      '3B40' : None, # reset
      '3B80' : 'd_steeringSpeak', # Dial button
      '3B90' : 'd_steeringSpeakLong', # Dial button, long press
      '3BA0' : None # Dial button, released
    }
  },
  '80' : {
    'BF' : {
      'ALL' : 'd_custom_IKE' # Use ALL to send all data to a particular function
    }
  },
  '68' : {
    '18' : {
      '01'     : '',
      '380000' : None, # d_cdSendStatus
      '380100' : None,
      '380300' : None,
      '380A00' : 'd_cdNext', # Next button on Radio
      '380A01' : 'd_cdPrev', # Prev button on Radio
      '380700' : None,
      '380701' : None,
      '380601' : None, # 1 pressed
      '380602' : None, # 2 pressed
      '380603' : None, # 3 pressed
      '380604' : None, # 4 pressed
      '380605' : None, # 5 pressed
      '380606' : None, # 6 pressed
      '380400' : None, # prev Playlist function?
      '380401' : None, # next Playlist function?
      '380800' : None,
      '380801' : None
    }
  },
  'C0' : {
    '68' : {
      '3100000B' : None, # Mode button pressed
      '3100134B' : None, # Mode button released
    }
  }
}

#####################################
# CONFIG
#####################################
TICK = 0.02 # sleep interval in seconds used between iBUS reads
AIRPLAY = False
WRITE_SESSION_TO_FILE = "/var/www/html/session.json" # If we should be writing collected data to a file at the webroot. False if we shouldn't be writing
LISTEN_FOR_EXTERNAL_COMMANDS = True # If we should open a port to listen for commands from network
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
  global WRITER, SESSION_CONTEXT, SESSION_SOCKET

  # Start ibus writer
  WRITER = writer
  pB_ticker.init(WRITER)
  
  # Init scanning for bluetooth every so often
  #pB_ticker.enableFunc("scanBluetooth", 20)

  # Start context for inter-protocol communication
  if(LISTEN_FOR_EXTERNAL_COMMANDS):
    SESSION_CONTEXT = zmq.Context()
    SESSION_SOCKET = SESSION_CONTEXT.socket(zmq.REP)
    zmq_address = "tcp://127.0.0.1:{}".format(LISTEN_SOCKET)
    SESSION_SOCKET.bind(zmq_address) 
    logging.info("Started ZMQ Socket at {}".format(zmq_address))

  # Init session data (will be written to network)
  updateSessionData("DOOR_LOCKED", False)
  updateSessionData("POWER_STATE", False)
  updateSessionData("SPEED", 0)
  updateSessionData("RPM", 0)

  # Turn on the 'clown nose' for 3 seconds
  WRITER.writeBusPacket('3F', '00', ['0C', '4E', '01'])

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
    pass
    #logging.debug("Exception from packet manager [%s]" % e)
    
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

  return result

# Listen for ibus messages, pass to packet manager if something substantial is found
def listen():
  global WRITE_SESSION_TO_FILE

  logging.info('Event listener initialized')
  while True:
    # Grab packet and manage appropriately
    packet = WRITER.readBusPacket()
    if packet:
      manage(packet)

    # Check external messages
    if LISTEN_FOR_EXTERNAL_COMMANDS:
      message = checkExternalMessages()
      if message:
        manageExternalMessages(message)

    # Write to session state to file if configured to
    if WRITE_SESSION_TO_FILE:
      updateSessionData("SESSION", True)

      try: 
        # Open file for writing session data
        session_file = open(WRITE_SESSION_TO_FILE,"w")
        session_file.write(json.dumps(SESSION_DATA))
        session_file.close()
      except Exception, e:
        logging.error("Encountered error when writing session to server file: [{}]".format(e))
        logging.debug("Turning off session file writes")
        WRITE_SESSION_TO_FILE = False

    time.sleep(TICK) # sleep a bit

# Handles various external messages, usually by calling an ibus directive
def manageExternalMessages(message):
  message_array = json.loads(message)
  logging.debug(message_array)

  # Directive / Bluetooth command verbatim
  if "directive" in message_array:
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

  # Non-blocking, as to not interrupt parsing ibus messages. We just queue messages instead
  try:
    message = SESSION_SOCKET.recv(zmq.NOBLOCK)
    logging.debug("Got External Message: {}".format(message))
    return message

  # IF no messages are queued
  except zmq.Again:
    return None
  except zmq.ZMQError, e:
    logging.error("Unexpected error when checking for external messages: [{}]".format(e))

# Abstracted updating session data, allows for easier logging of update timing
def updateSessionData(key, data):
  global SESSION_DATA
  now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
  SESSION_DATA[key] = data
  
  # Ensure proper key structures exist
  if "UPDATED_TIME" not in SESSION_DATA:
    SESSION_DATA["UPDATED_TIME"] = dict()
  if key not in SESSION_DATA["UPDATED_TIME"]:
    SESSION_DATA["UPDATED_TIME"][key] = None

  SESSION_DATA["UPDATED_TIME"][key] = now

  ##
  # TODO: for publish-subscribe setups, send latest data to clients
  ##

# Shutdown pyBus
def shutDown():
  global SESSION_SOCKET, SESSION_CONTEXT
  logging.debug("Killing tick utility")
  pB_ticker.shutDown()

  if LISTEN_FOR_EXTERNAL_COMMANDS:
    logging.debug("Destroying ZMQ socket")
    SESSION_SOCKET.close()
    SESSION_CONTEXT.destroy()

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
  updateSessionData("POWER_STATE", False)

def d_keyIn(packet):
  updateSessionData("POWER_STATE", True)

# Called whenever doors are locked.
def d_carLocked(packet = None):
  updateSessionData("DOOR_LOCKED_DRIVER", True)
  updateSessionData("DOOR_LOCKED_PASSENGER", True)

# Called whenever doors are unlocked.
def d_carUnlocked(packet = None):
  updateSessionData("DOOR_LOCKED_DRIVER", False)
  updateSessionData("DOOR_LOCKED_PASSENGER", False)

# Called whenever ONLY passenger door is locked
# This isn't very often, especially on coupe models
def d_passengerDoorLocked(packet):
  updateSessionData("DOOR_LOCKED_PASSENGER", True)

# Called whenever ONLY DRIVER door is locked
# This isn't very often, especially on coupe models
def d_driverDoorLocked(packet):
  updateSessionData("DOOR_LOCKED_DRIVER", True)

# This packet is used to parse all messages from the IKE (instrument control electronics), as it contains speed/RPM info. 
# But the data for speed/rpm will vary, so it must be parsed via a method linked to 'ALL' data in the JSON DIRECTIVES
def d_custom_IKE(packet):
  packet_data = packet['dat']

  # Ignition Status
  if packet_data[0] == '11':
    if (packet_data[1] == '00'): # Key Out.
      updateSessionData("POWER_STATE", False)
    elif (packet_data[1] == '01'): # Pos 1
      updateSessionData("POWER_STATE", "POS_1")
    elif (packet_data[1] == '03'): # Pos 2
      updateSessionData("POWER_STATE", "POS_2")
    elif (packet_data[1] == '07'): # Start
      updateSessionData("POWER_STATE", "START")

  # Sensor Status, broadcasted every 10 seconds
  elif packet_data[0] == '13':
    updateSessionData("IKE_SENSOR_STATUS", (packet_data[1]+packet_data[2]+packet_data[3]+packet_data[4]+packet_data[5]+packet_data[6]+packet_data[7]))

    # Byte 7 holds temp in c
    updateSessionData("OUTSIDE_TEMP_2", int(packet_data[7], 16))

  # Speed / RPM Info, broadcasted every 2 seconds
  elif packet_data[0] == '18':
    speed = int(packet_data[1], 16) * 2
    revs = int(packet_data[2], 16)

    updateSessionData("SPEED", speed)
    updateSessionData("RPM", revs*100)

  # Temperature Status, broadcasted every 10 seconds
  elif packet_data[0] == '19':
    updateSessionData("OUTSIDE_TEMP", int(packet_data[1], 16))
    updateSessionData("COOLANT_TEMP", int(packet_data[2], 16))

    # Only for european models I believe, or if you've set this to be tracked with INPA/NCS. Otherwise 0
    updateSessionData("OIL_TEMP", int(packet_data[3], 16))

  # OBC Estimated Range / Average Speed
  elif packet_data[0] == '24':
    if (packet_data[1] == '06'):
      updateSessionData("RANGE_KM", int((packet_data[3]+packet_data[4]+packet_data[5]+packet_data[6]), 16))
    elif (packet_data[1] == '0A'):
      updateSessionData("AVG_SPEED", int((packet_data[3]+packet_data[4]+packet_data[5]+packet_data[6]), 16))

# Handles messages sent when door/window status changes
def d_windowDoorMessage(packet):
  pass

def d_togglePause(packet):
  #pB_bt.togglePause()
  pass

def d_cdNext(packet):
  pass

def d_cdPrev(packet):
  pass

def d_steeringNext(packet):
  #pB_bt.nextTrack()
  pass

def d_steeringPrev(packet):
  #pB_bt.prevTrack()
  pass

def d_steeringSpeak(packet):
  toggleModeButton()

def d_steeringSpeakLong(packet):
  pass

################## DIRECTIVE UTILITY FUNCTIONS ##################

# Emulates pressing the "MODE" button on radio
def toggleModeButton():
  WRITER.writeBusPacket('C0', '68', ['31', '00', '00', '0B', '94']) # press
  WRITER.writeBusPacket('C0', '68', ['01', '00', '13', '4B', 'C7']) # release

# VERY loud, careful
def turnOnAlarm():
  WRITER.writeBusPacket('3F', '00', ['0C', '00', '55'])

# Turns on flashers, including interior light
def turnOnFlashers():
  WRITER.writeBusPacket('3F', '00', ['0C', '00', '5B'])

# Turns on hazards, including interior light
def turnOnHazards():
  WRITER.writeBusPacket('3F', '00', ['0C', '70', '01'])

# Slowly dim interior lights
def interiorLightsOff():
  WRITER.writeBusPacket('3F', '00', ['0C', '00', '59'])

def toggleDoorLocks():
  WRITER.writeBusPacket('3F','00', ['0C', '03', '01'])
  updateSessionData("DOOR_LOCKED_DRIVER", not SESSION_DATA["DOOR_LOCKED_DRIVER"])
  updateSessionData("DOOR_LOCKED_PASSENGER", not SESSION_DATA["DOOR_LOCKED_PASSENGER"])

def lockDoors():
  WRITER.writeBusPacket('3F','00', ['0C', '34', '01'])
  d_carLocked() # Trigger car locked function

def openTrunk():
  WRITER.writeBusPacket('3F','00', ['0C', '02', '01'])
  updateSessionData("TRUNK_OPEN", True)

# Roll all 4 windows up
def rollWindowsUp():
  WRITER.writeBusPacket('3F','00', ['0C', '53', '01']) # Put up window 1
  WRITER.writeBusPacket('3F','00', ['0C', '42', '01']) # Put up window 2
  WRITER.writeBusPacket('3F','00', ['0C', '55', '01']) # Put up window 3
  WRITER.writeBusPacket('3F','00', ['0C', '43', '01']) # Put up window 4
  updateSessionData("WINDOWS_STATUS", "UP")

# Roll all 4 windows down
def rollWindowsDown():
  WRITER.writeBusPacket('3F','00', ['0C', '52', '01']) # Put down window 1
  WRITER.writeBusPacket('3F','00', ['0C', '41', '01']) # Put down window 2
  WRITER.writeBusPacket('3F','00', ['0C', '54', '01']) # Put down window 3
  WRITER.writeBusPacket('3F','00', ['0C', '44', '01']) # Put down window 4
  updateSessionData("WINDOWS_STATUS", "DOWN")

# Pops up windows "a piece"
def popWindowsUp():
  WRITER.writeBusPacket('3F','00', ['0C', '53', '01']) # Pop up window 1
  WRITER.writeBusPacket('3F','00', ['0C', '55', '01']) # Pop up window 2
  WRITER.writeBusPacket('3F','00', ['0C', '42', '01']) # Pop up window 3
  WRITER.writeBusPacket('3F','00', ['0C', '43', '01']) # Pop up window 3
  updateSessionData("WINDOWS_STATUS", "UP") # this may not be 100% true

# Pops down windows "a piece"
def popWindowsDown():
  WRITER.writeBusPacket('3F','00', ['0C', '52', '01']) # Pop down window 1
  WRITER.writeBusPacket('3F','00', ['0C', '54', '01']) # Pop down window 2
  WRITER.writeBusPacket('3F','00', ['0C', '41', '01']) # Pop down window 3
  WRITER.writeBusPacket('3F','00', ['0C', '44', '01']) # Pop down window 3
  updateSessionData("WINDOWS_STATUS", "POPPED_DOWN")

# Put Convertible Top Down
def convertibleTopDown():
  #WRITER.writeBusPacket('3F', '00', ['0C', '99', '01'])
  WRITER.writeBusPacket('3F', '00', ['0C', '7E', '01'])
  #WRITER.writeBusPacket('3F', '00', ['0C', '00', '66'])

# Put Convertible Top Up
def convertibleTopUp():
  #WRITER.writeBusPacket('9C', 'BF', ['7C', '00', '71'])
  WRITER.writeBusPacket('3F', '00', ['0C', '7E', '01'])

# Tell IKE to set the time
def _setTime(day, month, year, hour, minute):
  # Check inputs to make sure we don't break things:
  for c in [day, month, year, hour, minute]:
    if not isinstance(c, int) or c > 255 or c < 0:
      return False

  logging.debug("Setting IKE time to {}/{}/{} {}:{}".format(day, month, year, hour, minute))

  # Write Hours : Minutes
  WRITER.writeBusPacket('3B', '80', ['40', '01', ('{:02x}'.format(hour)).upper(), ('{:02x}'.format(minute)).upper()])
  # Write Day/Month/Year
  WRITER.writeBusPacket('3B', '80', ['40', '02', ('{:02x}'.format(day)).upper(), ('{:02x}'.format(month)).upper(), ('{:02x}'.format(year)).upper()])

  return True

# Soft "alarm", no noise but makes the car very visible
def _softAlarm():
  turnOnFlashers()
  turnOnHazards()

#################################################################