############################################################################
# PYBUS SESSION DATA, USED TO STORE ALL THE CAR'S STATES
# WE CAN GET OUR GRUBBY HANDS ON.
#
# BY DEFAULT WRITTEN TO A FILE IN HTTP DIRECTORY FOR OTHER
# DEVICES TO PULL FROM.
#
# TODO: PUBLISH / SUBSCRIBE SETUPS
############################################################################

import datetime
import logging

json = None
zmq = None
MySQLdb = None

class ibusSession():

	# Define Session File path and Session Socket (ZMQ) port #, False to disable
	def __init__(self, init_session_file=False, init_session_socket=False, init_session_mysql=False):
		global json, zmq, MySQLdb

		# Empty dict for storing key:value pairs of log data
		#
		# TODO: Attempt to load from previous file to init with
		#
		self.data = {}
		self.modified = True
		self.db = None
		self.write_to_file = False

		# Open file for writing session data
		if init_session_file:
			import json, os
			if os.access(init_session_file, os.W_OK):
				self.updateData("SESSION", True)
				self.write_to_file = True
				self.filename = init_session_file
			else:
				logging.error("Session file {} is not writable, not enabling session IO.")

		# Start ZMQ socket for messaging
		if init_session_socket:
			import zmq
			self.context = zmq.Context()
			self.socket = self.context.socket(zmq.REP)
			zmq_address = "tcp://127.0.0.1:{}".format(init_session_socket)
			self.socket.bind(zmq_address) 
			logging.info("Started ZMQ Socket at {}.".format(zmq_address))

		# Start MySQL logging
		if init_session_mysql:
			import MySQLdb
			self.db = MySQLdb.connect("localhost", init_session_mysql[0], init_session_mysql[1], init_session_mysql[2])
			self.curs = self.db.cursor()

			# Check if table exists
			self.curs.execute("SHOW TABLES")
			texists = False
			for table in self.curs:
				if "log_serial" in table:
					texists = True
					break
			
			# Create table if not exist
			if not texists:
				self.curs.execute("CREATE TABLE log_serial (id INT AUTO_INCREMENT PRIMARY KEY, timestamp DATETIME, entry VARCHAR(255), value VARCHAR(255))")
				self.db.commit()

	# Read from previous session file
	def read(self, session_file):
		pass

	# Write to file, should only called if started with init_session_file
	def write(self):
		try: 
			if not self.write_to_file:
				logging.error("Something tried writing without a valid file. This shouldn't have happened.")
				return False

			# Open file for writing session data
			session_file = open(self.filename, "w")
			session_file.write(json.dumps(self.data))
			session_file.close()

			# Mark as unmodified since last write
			self.modified = False

		except Exception, e:
			logging.error("Failed to write session to file: [{}]".format(e))
			logging.error("Turning off session file writes.")
			self.write_to_file = False

	# Allows for easier logging of update timing
	#
	# TODO: for publish-subscribe setups, send latest data to clients
	#
	def updateData(self, key, data):
		now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
		self.data[key] = data
		
		# Ensure proper key structures exist
		if "UPDATED_TIME" not in self.data:
			self.data["UPDATED_TIME"] = dict()
		if key not in self.data["UPDATED_TIME"]:
			self.data["UPDATED_TIME"][key] = None

		self.data["UPDATED_TIME"][key] = now

		# Write entry to massive DB table
		if self.db:
			try:
				self.curs.execute("""INSERT INTO log_serial
					(timestamp, entry, value) values  (%s, %s, %s) """, 
					(now, key, data))
				self.db.commit()
			except Exception, e:
				logging.error("Failed to write MySQL entry: [{}]".format(e))

		# Mark as modified, session change should be written
		self.modified = True
		
	# Checks for any external messages sent to socket,
	def checkExternalMessages(self):

		# Non-blocking, to not interrupt parsing ibus messages. We just queue messages instead
		try:
			message = self.socket.recv(zmq.NOBLOCK)
			logging.info("Got External Message: {}".format(message))
			return message

		# IF no messages are queued
		except zmq.Again:
			return None
		except zmq.ZMQError, e:
			logging.error("Checking for external messages failed: [{}]".format(e))

	# Shutdown, cleanup where necessary
	def close(self):
		logging.info("Closing pyBus Session.")

		# One last write for posterity
		self.write()

		logging.info("Destroying ZMQ socket.")
		self.socket.close()
		self.context.destroy()
