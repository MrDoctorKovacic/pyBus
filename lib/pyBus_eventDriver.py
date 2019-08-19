#!/usr/bin/python

import os
import sys
import time
import json
import signal
import random
import logging as pybusLog
import traceback
import datetime
import requests
import ast

#import pyBus_tickUtil as pB_ticker # Ticker for signals requiring intervals
import pyBus_session as pB_session # Session object for writing and sending log info abroad
import pyBus_utilities as utils
import pyBus_directives as directives

# This module will read a packet, match it against the json object 'DIRECTIVES' below. 
# The packet is checked by matching the source value in packet (i.e. where the packet came from) to a key in the object if possible
# Then matching the Destination if possible
# The joining the 'data' component of the packet and matching that if possible.
# The resulting value will be the name of a function to pass the packet to for processing of sorts.

#####################################
# CONFIG
#####################################
TICK = 0.04 # sleep interval in seconds used between iBUS reads

#####################################
# Define Globals
#####################################
WRITER = None
SESSION = None
WITH_API = False
MEDIA_HOST = "http://lucio.local:5353"

#####################################
# FUNCTIONS
#####################################
# Set the WRITER object (the iBus interface class) to an instance passed in from the CORE module
def init(writer, args):
	global WRITER, SESSION, WITH_API

	# Determine if we're extending functionality with external MDroid-Core API
	if args and args["with_api"]:
		WITH_API = args["with_api"]
	else:
		if args:
			pybusLog.info("Not using MDroid API, despite finding the following config:")
			pybusLog.info(str(args))
		WITH_API = False

	# Start ibus writer
	WRITER = writer

	# Start PyBus pybusLog Session
	SESSION = pB_session.ibusSession(WITH_API)

	# Turn on the 'clown nose' for 3 seconds
	WRITER.writeBusPacket('3F', '00', ['0C', '4E', '01'])

	# Set date/time. Redundant, but helps easily diagnose what time the Pi THINKS it is
	now = datetime.datetime.now()
	utils.setTime(now.day, now.month, now.year, now.hour, now.minute)

# Manage the packet, meaning traverse the JSON 'DIRECTIVES' object and attempt to determine a suitable function to pass the packet to.
def manage(packet):
	src = packet['src']
	dst = packet['dst']
	dataString = ''.join(packet['dat'])
	methodName = None

	try:
		# First check if the src / dest is mapped in directives dict above
		if src in directives.LIST and dst in directives.LIST[src]:
			dstDir = directives.LIST[src][dst]
			if ('ALL'  in dstDir.keys()):
				methodName = dstDir['ALL']
			elif (dataString in dstDir):
				methodName = dstDir[dataString]
			elif ('OTHER' in dstDir.keys()):
				methodName = dstDir['OTHER']
	except Exception, e:
		pybusLog.debug("Exception from packet manager [%s]" % e)
		
	result = None
	if methodName != None:
		methodToCall = directives.getDirectives().get(methodName, None)
		if methodToCall:
			pybusLog.info("Directive found for packet - %s" % methodName)
			try:
				result = methodToCall(packet)
			except:
				pybusLog.error("Exception raised from [%s]" % methodName)
				pybusLog.error(traceback.format_exc())
		
		else:
			pybusLog.warning("Method (%s) does not exist" % methodName)

	return result

# Listen for ibus messages, pass to packet manager if something substantial is found
def listen(kwargs):
	pybusLog.info('Event listener initialized')
	while True:
		try:
			# Grab packet and manage appropriately
			packet = WRITER.readBusPacket()
			if packet:
				manage(packet)

			time.sleep(TICK) # sleep a bit
		except Exception, e:
			# If an exception bubbles up this far, we've really messed up
			print "CAUGHT OTHERWISE FATAL ERROR IN MAIN THREAD:\n{}".format(e)

# Handles various external messages recieved from the HTTP server
def handleExternalMessages(message):
	try:
		# Check if we have raw data first
		if message[0] == '[':
			# this is dangerous without auth, and even then I don't like it
			parsedList = ast.literal_eval(str(message))
			if parsedList and len(parsedList) == 3 and len(parsedList[0]) == 2 and len(parsedList[1]) == 2:
				parsedData = [parsedList[2][i:i+2] for i in range(0, len(parsedList[2]), 2)]
				WRITER.writeBusPacket(parsedList[0], parsedList[1], parsedData)
				response = "OK" # 10-4
		else:
			methodToCall = utils.getUtilities().get(message, None)

			# Check if this function exists at all
			if not methodToCall:
				response = "Utility function {} does not exist".format(message)
				pybusLog.info("Sending response: {}".format(response))
				return response

			# Call the utility function
			data = methodToCall()

			# Either send (requested) data or an acknowledgement back to node
			response = json.dumps(data) if data else "OK"

			pybusLog.info("Sending response: {}".format(response))

		return response

	except Exception, e:
		pybusLog.error("Failed to call directive from external command.\n{}".format(e))

# Shutdown pyBus
def shutDown():
	pybusLog.info("Killing tick utility.")
	#pB_ticker.shutDown()