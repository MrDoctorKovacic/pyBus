#!/usr/bin/python

import os
import sys
import time
import signal
import traceback
import logging
import argparse
import gzip
import json
import pyBus_core as core

#####################################
# FUNCTIONS
#####################################
# Manage Ctrl+C gracefully
def signal_handler_quit(signal, frame):
	logging.info("Shutting down pyBus.")
	core.shutdown()
	sys.exit(0)

# Print basic usage
def print_usage():
	print "Intended Use:"
	print "%s <PATH_TO_DEVICE>" % (sys.argv[0])
	print "Eg: %s /dev/ttyUSB0" % (sys.argv[0])
  
#################################
# Configure Logging for pySel
#################################
def configureLogging(numeric_level):
	if not isinstance(numeric_level, int):
		numeric_level=0
	logging.basicConfig(
		level=numeric_level,
		format='[%(levelname)s in %(threadName)s] %(message)s', 
		datefmt='')
  
def createParser():
	parser = argparse.ArgumentParser()
	parser.add_argument('-v', '--verbose', action='store', default=20, type=int, help='Increases verbosity of logging.')
	parser.add_argument('--settings-file', action='store', help='Config file to load Device and API settings.')
	return parser

#####################################
# MAIN
#####################################
parser   = createParser()
args  = parser.parse_args()
loglevel = args.verbose
_startup_cwd = os.getcwd()

signal.signal(signal.SIGINT, signal_handler_quit) # Manage Ctrl+C
configureLogging(loglevel)

devPath = "/dev/ttyUSB0"
core.DEVPATH = "/dev/ttyUSB0"

config = dict()

# Overwrite defaults if settings file is provided
if args.settings_file:
	if os.path.isfile(args.settings_file): 
		try:
			with open(args.settings_file) as json_file:
				data = json.load(json_file)
				if "MDROID" in data:
					# Setup MDroid API
					if "MDROID_HOST" in data["MDROID"]:
						config["with_api"] = data["MDROID"]["MDROID_HOST"]
					else:
						logging.debug("MDROID_HOST not found in config file, not using MDroid API.")

					# Setup device
					if "PYBUS_DEVICE" in data["MDROID"]:
						devPath = data["MDROID"]["PYBUS_DEVICE"]
						core.DEVPATH = data["MDROID"]["PYBUS_DEVICE"]
					else: 
						logging.debug("PYBUS_DEVICE not found in config file, using defaults.")

		except IOError as e:
			logging.error("Failed to open settings file:"+args.settings_file)
			logging.error(e)
	else:
		logging.error("Could not load settings from file"+str(args.settings_file))

# Make requests a little quieter
logging.getLogger("requests").setLevel(logging.ERROR)

try:
	core.initialize(config)
	core.run()
except Exception:
	logging.error("Caught unexpected exception:\n{}".format(traceback.format_exc()))
	logging.critical("And I'm dead.")    
	sys.exit(0)
