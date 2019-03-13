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

import pyBus_tickUtil as pB_ticker # Ticker for signals requiring intervals
import pyBus_session as pB_session # Session object for writing and sending log info abroad

# Optional modules to be imported conditionally
pB_bt = None

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
			''
			'0C3401' : 'd_carUnlocked', # All doors unlocked
			'0C4601' : 'd_passengerDoorLocked',
			'0C4701' : 'd_driverDoorLocked',
			'OTHER'  : 'd_diagnostic'
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
			'019A' : 'restartBoard', # RT Button
			'3B40' : None, # reset
			'3B80' : 'd_steeringSpeak', # Dial button
			'3B90' : 'd_steeringSpeakLong', # Dial button, long press
			'3BA0' : None # Dial button, released
		},
		'FF' : {
			'3B40' : 'd_steeringRT' # also RT Button?
		}
	},
	'5B' : {
		'80' : {
			'ALL' : 'd_climateControl'
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
	'80' : {
		'BF' : {
			'ALL' : 'd_custom_IKE' # Use ALL to send all data to a particular function
		}
	},
	'C0' : {
		'68' : {
			'3100000B' : None, # Mode button pressed
			'3100134B' : None, # Mode button released
		}
	},
	'C0' : { # telephone module
		'80' : { # IKE
			'234220' : 'd_steeringRT' # Telephone invoked (from steering wheel?)
		}
	},
	'E8' : {
		'D0' : {
			'ALL' : 'd_rainLightSensor'
		}
	}
}

#####################################
# CONFIG
#####################################
TICK = 0.04 # sleep interval in seconds used between iBUS reads

#####################################
# Define Globals
#####################################
WRITER = None
SESSION = None
SESSION_FILE = None
LISTEN_FOR_EXTERNAL_COMMANDS = False
LISTEN_PORT = None
MYSQL_CRED = None
MEDIA_PLAYER = None
EXTERNAL_JSON = None

#####################################
# FUNCTIONS
#####################################
# Set the WRITER object (the iBus interface class) to an instance passed in from the CORE module
def init(writer, args):
	global pB_bt, WRITER, SESSION, SESSION_FILE, LISTEN_FOR_EXTERNAL_COMMANDS, LISTEN_PORT, MYSQL_CRED, MEDIA_PLAYER, EXTERNAL_JSON

	#
	# Parse sys arguments to set up optional data loging modules
	#

	# Setup Bluetooth
	if args.with_bt:
		import pyBus_bluetooth as pB_bt # For bluetooth audio controls
		logging.debug("Setting Bluetooth address to {}. Attempting to connect.".format({args.with_bt}))
		MEDIA_PLAYER = args.with_bt

		# Attempt to connect phone through bluetooth, 
		# Non-blocking, do before waiting on clear ibus
		pB_bt.connect(MEDIA_PLAYER)
		pB_bt.playDelayed(MEDIA_PLAYER)

	# Setup ZMQ
	if args.with_zmq:
		# Session object for writing and sending log info abroad
		LISTEN_FOR_EXTERNAL_COMMANDS = True
		LISTEN_PORT = args.with_zmq

	# Setup Session IO
	if args.with_session:
		# Session file, stored onto disk
		SESSION_FILE = args.with_session

	# Setup External JSON
	if args.with_ext_session:
		# Parse each external JSON location, along with fetch frequency
		for external_location in args.with_ext_session:
			logging.info(external_location)
		EXTERNAL_JSON = args.with_ext_session

	# Setup MySQL
	if args.with_mysql:
		# Session object for writing and sending log info abroad
		MYSQL_CRED = args.with_mysql

	#
	# End argument/module parsing
	#

	# Start ibus writer
	WRITER = writer
	pB_ticker.init(WRITER)

	# Start PyBus logging Session
	SESSION = pB_session.ibusSession(SESSION_FILE, LISTEN_PORT, MYSQL_CRED, EXTERNAL_JSON)

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
		elif (dataString in dstDir):
			methodName = dstDir[dataString]
		elif ('OTHER' in dstDir.keys()):
			methodName = dstDir['OTHER']
	except Exception, e:
		logging.debug("Exception from packet manager [%s]" % e)
		
	result = None
	if methodName != None:
		methodToCall = globals().get(methodName, None)
		if methodToCall:
			logging.info("Directive found for packet - %s" % methodName)
			try:
				result = methodToCall(packet)
			except:
				logging.error("Exception raised from [%s]" % methodName)
				logging.error(traceback.format_exc())
		
		else:
			logging.warning("Method (%s) does not exist" % methodName)

	return result

# Listen for ibus messages, pass to packet manager if something substantial is found
def listen():
	logging.info('Event listener initialized')
	while True:
		# Grab packet and manage appropriately
		packet = WRITER.readBusPacket()
		if packet:
			manage(packet)

		# Check external messages
		if LISTEN_FOR_EXTERNAL_COMMANDS:
			message = SESSION.checkExternalMessages()
			if message:
				manageExternalMessages(message)

		# Check external JSON sessions
		# This will end up happening at every well defined interval going forward
		if EXTERNAL_JSON:
			for ext in SESSION.external_locations:
				if ext.timeToFetch <= 0:
					try:
						ext_json_array = json.loads(ext.fetch())
						for obj in ext_json_array:
							SESSION.updateData(obj, ext_json_array[obj])
					except Exception, e:
						logging.error("Failed to load JSON into live session.")
						logging.error(e)
					ext.timeToFetch = ext.interval
				else:
					ext.timeToFetch -= TICK

		# Write all this to a file
		if SESSION and SESSION.write_to_file and SESSION.modified:
			SESSION.write()

		time.sleep(TICK) # sleep a bit

# Shutdown pyBus
def shutDown():
	if LISTEN_FOR_EXTERNAL_COMMANDS:
		SESSION.close()

	logging.info("Killing tick utility.")
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
	SESSION.updateData("POWER_STATE", False)
	SESSION.updateData("RPM", 0)
	SESSION.updateData("SPEED", 0)
	if pB_bt: pB_bt.pause()

def d_keyIn(packet):
	SESSION.updateData("POWER_STATE", True)
	if pB_bt: pB_bt.play()

# Called whenever doors are locked.
def d_carLocked(packet = None):
	SESSION.updateData("DOOR_LOCKED_DRIVER", True)
	SESSION.updateData("DOOR_LOCKED_PASSENGER", True)

# Called whenever ALL doors are unlocked.
def d_carUnlocked(packet = None):
	SESSION.updateData("DOOR_LOCKED_DRIVER", False)
	SESSION.updateData("DOOR_LOCKED_PASSENGER", False)

# Called whenever ONLY passenger door is locked
# This isn't very often, especially on coupe models
def d_passengerDoorLocked(packet):
	SESSION.updateData("DOOR_LOCKED_PASSENGER", True)

# Called whenever ONLY DRIVER door is locked
# This isn't very often, especially on coupe models
def d_driverDoorLocked(packet):
	SESSION.updateData("DOOR_LOCKED_DRIVER", True)

# This packet is used to parse all messages from the IKE (instrument control electronics), as it contains speed/RPM info. 
# But the data for speed/rpm will vary, so it must be parsed via a method linked to 'ALL' data in the JSON DIRECTIVES
def d_custom_IKE(packet):
	packet_data = packet['dat']

	# Ignition Status
	if packet_data[0] == '11':
		if (packet_data[1] == '00'): # Key Out.
			SESSION.updateData("POWER_STATE", False)
		elif (packet_data[1] == '01'): # Pos 1
			SESSION.updateData("POWER_STATE", "POS_1")
		elif (packet_data[1] == '03'): # Pos 2
			SESSION.updateData("POWER_STATE", "POS_2")
		elif (packet_data[1] == '07'): # Start
			SESSION.updateData("POWER_STATE", "START")

	# Sensor Status, broadcasted every 10 seconds
	elif packet_data[0] == '13':
		SESSION.updateData("IKE_SENSOR_STATUS", (packet_data[1]+packet_data[2]+packet_data[3]+packet_data[4]+packet_data[5]+packet_data[6]+packet_data[7]))

		# Byte 7 holds temp in c
		SESSION.updateData("OUTSIDE_TEMP_2", int(packet_data[7], 16))

	# Speed / RPM Info, broadcasted every 2 seconds
	elif packet_data[0] == '18':
		speed = int(packet_data[1], 16) * 2
		revs = int(packet_data[2], 16)

		SESSION.updateData("SPEED", speed)
		SESSION.updateData("RPM", revs*100)

	# Temperature Status, broadcasted every 10 seconds
	elif packet_data[0] == '19':
		SESSION.updateData("OUTSIDE_TEMP", int(packet_data[1], 16))
		SESSION.updateData("COOLANT_TEMP", int(packet_data[2], 16))

		# Only for european models I believe, or if you've set this to be tracked with INPA/NCS. Otherwise 0
		SESSION.updateData("OIL_TEMP", int(packet_data[3], 16))

	# OBC Estimated Range / Average Speed
	elif packet_data[0] == '24':
		if (packet_data[1] == '06'):
			SESSION.updateData("RANGE_KM", int((packet_data[3]+packet_data[4]+packet_data[5]+packet_data[6]), 16))
		elif (packet_data[1] == '0A'):
			SESSION.updateData("AVG_SPEED", int((packet_data[3]+packet_data[4]+packet_data[5]+packet_data[6]), 16))

# Handles messages sent when door/window status changes
def d_windowDoorMessage(packet):
	pass

# Handles Rain/Light sensor data. TODO: find what light/dark is and wet/dry is
def d_rainLightSensor(packet):
	SESSION.updateData("RAIN_LIGHT_SENSOR_STATUS", (''.join(packet['dat'])))

# Handles raw climate control (Integrated Heating And Air Conditioning) data
def d_climateControl(packet):
	SESSION.updateData("CLIMATE_CONTROL_STATUS", (''.join(packet['dat'])))

# Handles any unknown diagnostic packets for logging
def d_diagnostic(packet):
	SESSION.updateData("DIAGNOSTIC", (''.join(packet['dat'])))

def d_togglePause(packet):
	if pB_bt: logging.debug(pB_bt.togglePause(MEDIA_PLAYER))

def d_cdNext(packet):
	pass

def d_cdPrev(packet):
	pass

def d_steeringNext(packet):
	if pB_bt: pB_bt.nextTrack(MEDIA_PLAYER)

def d_steeringPrev(packet):
	if pB_bt: pB_bt.prevTrack(MEDIA_PLAYER)

def d_steeringRT(packet):
	pressMode()

def d_steeringSpeak(packet):
	pressMode()

def d_steeringSpeakLong(packet):
	pass

############################################################################
# UTILITY FUNCTIONS
# THESE ARE USED FOR INTERNAL OR EXTERNAL DIRECTIVES, 
# OFTEN COMBINING SEVERAL IBUS WRITES INTO ONE FUNCTION
#
# TYPICALLY DIRECTIVES ARE REACTIVE, THESE UTLITIES ARE ACTIVE
############################################################################

# Restarts the SBC this is running on
def restartBoard():
	shutDown()
	os.system('reboot now')

# Emulates pressing the "MODE" button on stereo
# Very useful for changing back to AUX input without using the stock radio
def pressMode():
	# If you're switching to radio, 
	# prepare to be spammed with Radio station song/artist/location/signal strength packets.
	# This will probably freeze the WRITER for 10+ seconds
	WRITER.writeBusPacket('F0', '68', ['48', '23']) # push
	WRITER.writeBusPacket('F0', '68', ['48', 'A3']) # release

# Press number pad, 1-6
# On radio this will switch to that assigned station
# On aux this will adjust the gain
def pressNumPad(number=6):
	if(number == 1):
		WRITER.writeBusPacket('F0', '68', ['48', '11']) # push
		WRITER.writeBusPacket('F0', '68', ['48', '91']) # release
	elif(number == 2):
		WRITER.writeBusPacket('F0', '68', ['48', '01']) # push
		WRITER.writeBusPacket('F0', '68', ['48', '81']) # release
	elif(number == 3):
		WRITER.writeBusPacket('F0', '68', ['48', '12']) # push
		WRITER.writeBusPacket('F0', '68', ['48', '92']) # release
	elif(number == 4):
		WRITER.writeBusPacket('F0', '68', ['48', '02']) # push
		WRITER.writeBusPacket('F0', '68', ['48', '82']) # release
	elif(number == 5):
		WRITER.writeBusPacket('F0', '68', ['48', '13']) # push
		WRITER.writeBusPacket('F0', '68', ['48', '93']) # release
	elif(number == 6):
		WRITER.writeBusPacket('F0', '68', ['48', '03']) # push
		WRITER.writeBusPacket('F0', '68', ['48', '83']) # release

# This switches to AM, I forget what pressing twice does
def pressAM():
	WRITER.writeBusPacket('F0', '68', ['48', '21']) # push
	WRITER.writeBusPacket('F0', '68', ['48', 'A1']) # release

# This switches to FM, I forget what pressing twice does
def pressFM():
	WRITER.writeBusPacket('F0', '68', ['48', '31']) # push
	WRITER.writeBusPacket('F0', '68', ['48', 'B1']) # release

# Presses next button on Radio, changing stations or songs
def pressNext():
	WRITER.writeBusPacket('F0', '68', ['48', '00']) # push
	WRITER.writeBusPacket('F0', '68', ['48', '80']) # release

# Presses prev button on Radio, changing stations or songs
def pressPrev():
	WRITER.writeBusPacket('F0', '68', ['48', '10']) # push
	WRITER.writeBusPacket('F0', '68', ['48', '90']) # release

# Presses on the left dial, turning stereo on & off
def pressStereoPower():
	WRITER.writeBusPacket('F0', '68', ['48', '06']) # push
	WRITER.writeBusPacket('F0', '68', ['48', '86']) # release

# VERY loud, careful
def turnOnAlarm():
	WRITER.writeBusPacket('3F', '00', ['0C', '00', '55'])

# NW
# Turns on flashers, including interior light
def turnOnFlashers():
	WRITER.writeBusPacket('3F', '00', ['0C', '00', '5B'])

# NW
# Turns on hazards, including interior light
def turnOnHazards():
	WRITER.writeBusPacket('3F', '00', ['0C', '70', '01'])

# NW
# Slowly dim interior lights
def interiorLightsOff():
	WRITER.writeBusPacket('3F', '00', ['0C', '00', '59'])

def toggleDoorLocks():
	WRITER.writeBusPacket('3F','00', ['0C', '03', '01'])
	SESSION.updateData("DOOR_LOCKED_DRIVER", not SESSION.data["DOOR_LOCKED_DRIVER"])
	SESSION.updateData("DOOR_LOCKED_PASSENGER", not SESSION.data["DOOR_LOCKED_PASSENGER"])

def lockDoors():
	WRITER.writeBusPacket('3F','00', ['0C', '34', '01'])
	d_carLocked() # Trigger car locked function

def openTrunk():
	WRITER.writeBusPacket('3F','00', ['0C', '02', '01'])
	SESSION.updateData("TRUNK_OPEN", True)

# Roll all 4 windows up
def rollWindowsUp():
	WRITER.writeBusPacket('3F','00', ['0C', '53', '01']) # Put up window 1
	WRITER.writeBusPacket('3F','00', ['0C', '42', '01']) # Put up window 2
	WRITER.writeBusPacket('3F','00', ['0C', '55', '01']) # Put up window 3
	WRITER.writeBusPacket('3F','00', ['0C', '43', '01']) # Put up window 4
	SESSION.updateData("WINDOWS_STATUS", "UP")

# Roll all 4 windows down
def rollWindowsDown():
	WRITER.writeBusPacket('3F','00', ['0C', '52', '01']) # Put down window 1
	WRITER.writeBusPacket('3F','00', ['0C', '41', '01']) # Put down window 2
	WRITER.writeBusPacket('3F','00', ['0C', '54', '01']) # Put down window 3
	WRITER.writeBusPacket('3F','00', ['0C', '44', '01']) # Put down window 4
	SESSION.updateData("WINDOWS_STATUS", "DOWN")

# NW
# Pops up windows "a piece"
def popWindowsUp():
	WRITER.writeBusPacket('3F','00', ['0C', '53', '01']) # Pop up window 1
	WRITER.writeBusPacket('3F','00', ['0C', '55', '01']) # Pop up window 2
	WRITER.writeBusPacket('3F','00', ['0C', '42', '01']) # Pop up window 3
	WRITER.writeBusPacket('3F','00', ['0C', '43', '01']) # Pop up window 3
	SESSION.updateData("WINDOWS_STATUS", "UP") # this may not be 100% true

# NW
# Pops down windows "a piece"
def popWindowsDown():
	WRITER.writeBusPacket('3F','00', ['0C', '52', '01']) # Pop down window 1
	WRITER.writeBusPacket('3F','00', ['0C', '54', '01']) # Pop down window 2
	WRITER.writeBusPacket('3F','00', ['0C', '41', '01']) # Pop down window 3
	WRITER.writeBusPacket('3F','00', ['0C', '44', '01']) # Pop down window 3
	SESSION.updateData("WINDOWS_STATUS", "POPPED_DOWN")

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

	logging.info("Setting IKE time to {}/{}/{} {}:{}".format(day, month, year, hour, minute))

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

# Handles various external messages, usually by calling an ibus directive
def manageExternalMessages(message):
	message_array = json.loads(message)
	logging.debug(message_array)

	# Directive / Bluetooth command verbatim
	if "directive" in message_array:
		try:
			# Messy, but calls a directive given the chance
			methodToCall = globals().get(message_array["directive"], None)
			data = methodToCall()

			# Either send (requested) data or an acknowledgement back to node
			if data is not None:
				response = json.dumps(data)
			else:
				response = "OK" # 10-4
			SESSION.socket.send(response) 

			logging.info("Sending response: {}".format(response))

		except Exception, e:
			logging.error("Failed to call directive from external command.\n{}".format(e))