#!/usr/bin/python

import os
import sys
import time
import json
import signal
import logging
import binascii
import subprocess
from time import strftime as date
import thread
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer

sys.path.append( './lib/' )

import pyBus_eventDriver as pB_eDriver # For responding to signals

from pyBus_interface import ibusFace
#####################################
# GLOBALS
#####################################
DEVPATH           = "/dev/ttyUSB0" # This is a default, but its always overridden. So not really a default.
IBUS              = None
PORT_NUMBER 	  = 8080

#####################################
# FUNCTIONS

# Initializes modules as required and opens files for writing
def initialize(args):
	global IBUS, DEVPATH
	
	# Initialize the iBus interface or wait for it to become available.
	while IBUS == None:
		if os.path.exists(DEVPATH):
			IBUS = ibusFace(DEVPATH)
		else:
			logging.warning("USB interface not found at (%s). Waiting 1 seconds.", DEVPATH)
			time.sleep(2)
	IBUS.waitClearBus() # Wait for the iBus to clear, then send some initialization signals
	
	pB_eDriver.init(IBUS, args)
	
# close the USB device and whatever else is required
def shutdown():
	global IBUS
	logging.info("Shutting down event driver")
	pB_eDriver.shutDown()
	
	if IBUS:
		logging.info("Killing iBUS instance")
		IBUS.close()
		IBUS = None

def run():
	try:
		# Open up HTTP server to listen on the network
		thread.start_new_thread(startHTTPServer, (None,))

		# Start listening locally on serial bus
		thread.start_new_thread(pB_eDriver.listen, (None,))
	except Exception, e:
		logging.error("Error: unable to start threads: %s" % e)
		shutdown()

# Additional HTTP server to recieve external messages
class pybusServer(BaseHTTPRequestHandler):
	
	# Handler for the GET requests
	def do_GET(self):
		try:
			utilityResponse = pB_eDriver.handleExternalMessages(self.path.replace("/", ""))
			if utilityResponse == "OK":
				self.send_response(200)
				self.end_headers()
				self.wfile.write("OK")
			else:
				self.send_error(404, 'Message does not match any known utilities: {}\n{}'.format(self.path, utilityResponse))
			return

		except Exception, e:
			self.send_error(404,'Error parsing utility: {}\n{}'.format(self.path, e))

# Server for handling external requests
def startHTTPServer(kwargs):
	server = HTTPServer(('', PORT_NUMBER), pybusServer)
	server.serve_forever()
	logging.info('Started pybus server on port {}'.format(PORT_NUMBER))