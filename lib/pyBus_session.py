############################################################################
# PYBUS SESSION
# USED AS INTERFACE BETWEEN PYBUS AND A CENTRAL REST API
############################################################################

import logging
import requests

zmq = None

class ibusSession():

	# Define Session File path and Session Socket (ZMQ) port #, False to disable
	def __init__(self, init_with_api=False, init_session_socket=False):
		global zmq

		# Make requests a little quieter
		logging.getLogger("requests").setLevel(logging.CRITICAL)
		logging.getLogger("urllib3").setLevel(logging.CRITICAL)

		# if we're extending functionality with external GoQMW API
		self.API = init_with_api

		# Start ZMQ socket for messaging
		if init_session_socket:
			import zmq
			self.context = zmq.Context()
			self.socket = self.context.socket(zmq.REP)
			zmq_address = "tcp://127.0.0.1:{}".format(init_session_socket)
			self.socket.bind(zmq_address)
			logging.info("Started ZMQ Socket at {}.".format(zmq_address))

		# Use a local dict instead of a remote one
		if not self.API:
			self.data = dict()

	# Allows for easier logging of update timing
	def updateData(self, key, data):
		# Write entry to main REST server
		if self.API:
			r = requests.post("http://localhost:5353/session/"+key, json={"value": str(data)}, headers={'Content-type': 'application/json', 'Accept': 'text/plain'})
			if r.status_code != 200:
				logging.debug("Failed to POST data to API: "+r.reason)
		else:
			self.data[key] = data

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
		logging.info("Destroying ZMQ socket.")
		self.socket.close()
		logging.info("Closing pyBus Session.")
		self.context.destroy()