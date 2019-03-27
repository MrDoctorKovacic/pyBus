#!/usr/bin/python

import os
import sys
import time
import signal
import traceback
import logging
import argparse
import gzip
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
    format='%(asctime)s [%(levelname)s in %(module)s] %(message)s', 
    datefmt='%Y/%m/%dT%I:%M:%S'
  )
  
def createParser():
  parser = argparse.ArgumentParser()
  parser.add_argument('-v', '--verbose', action='store', default=20, type=int, help='Increases verbosity of logging.')
  parser.add_argument('--device', action='store', required=True, help='Path to iBus interface.')
  parser.add_argument('--with-zmq', action='store', help='ZMQ port to listen on.')
  parser.add_argument('--with-session', action='store', help='File to output momentary session.')
  parser.add_argument('--with-mysql', action='store', nargs=3, help='MySQL Username, Password, and Database to log session. Table log_serial will be created if it does not exist.')
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

devPath = args.device if args.device else "/dev/ttyUSB0"
core.DEVPATH = devPath if devPath else "/dev/ttyUSB0"

# Conditionally import ZMQ
if args.with_zmq:
	import zmq

try:
  core.initialize(args)
  core.run()
except Exception:
  logging.error("Caught unexpected exception:\n{}".format(traceback.format_exc()))

logging.critical("And I'm dead.")    
sys.exit(0)
