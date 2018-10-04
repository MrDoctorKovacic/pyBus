############################################################################
# PYBUS SESSION DATA, USED TO STORE ALL THE CAR'S STATES
# WE CAN GET OUR GRUBBY HANDS ON.
#
# BY DEFAULT WRITTEN TO A FILE IN HTTP DIRECTORY FOR OTHER
# DEVICES TO PULL FROM.
#
# TODO: PUBLISH / SUBSCRIBE SETUPS
############################################################################

import json
import datetime
import logging
import zmq


class ibusSession():

	# Define Session File path and Session Socket (ZMQ) port #, False to disable
	def __init__(self, init_session_file=False, init_session_socket=False):

		# Empty dict for storing key:value pairs of log data
		#
		# TODO: Attempt to load from previous file to init with
		#
		self.data = {}
		self.socket = None

		# Open file for writing session data
		if(init_session_file):
			self.updateData("SESSION", True)
			self.write_to_file = True
			self.filename = init_session_file

		# Start ZMQ socket for messaging
		if(init_session_socket):
			self.context = zmq.Context()
			self.socket = self.context.socket(zmq.REP)
			zmq_address = "tcp://127.0.0.1:{}".format(init_session_socket)
			self.socket.bind(zmq_address) 
			logging.info("Started ZMQ Socket at {}".format(zmq_address))

	# Read from previous session file
	def read(self, session_file):
		pass

	# Write to file, if applicable
	def write(self):
		try: 
			# Open file for writing session data
			session_file = open(self.filename, "w")
			session_file.write(json.dumps(self.data))
			session_file.close()
		except Exception, e:
			logging.error("Encountered error when writing session to server file: [{}]".format(e))
			logging.debug("Turning off session file writes")
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

	# Handles various external messages, usually by calling an ibus directive
	def manageExternalMessages(self, message):
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
				self.socket.send(response) 

			except Exception, e:
				logging.error("Failed to call directive from external command.\n{}".format(e))

	# Checks for any external messages sent to socket,
	def checkExternalMessages(self):

		# Non-blocking, as to not interrupt parsing ibus messages. We just queue messages instead
		try:
			message = self.socket.recv(zmq.NOBLOCK)
			logging.debug("Got External Message: {}".format(message))
			return message

		# IF no messages are queued
		except zmq.Again:
			return None
		except zmq.ZMQError, e:
			logging.error("Unexpected error when checking for external messages: [{}]".format(e))

	# Shutdown, cleanup where necessary
	def close(self):
		logging.debug("Closing pyBus Session")

		# One last write for posterity
		self.write()

		logging.debug("Destroying ZMQ socket")
		self.socket.close()
		self.context.destroy()
