############################################################################
# PYBUS SESSION
# USED AS INTERFACE BETWEEN PYBUS AND A CENTRAL REST API
############################################################################

import logging
import requests

class ibusSession():

	# Define MDroid-Core api url if applicable
	def __init__(self, init_with_api=False):

		# Make requests a little quieter
		logging.getLogger("requests").setLevel(logging.CRITICAL)
		logging.getLogger("urllib3").setLevel(logging.CRITICAL)

		# if we're extending functionality with external MDroid-Core
		self.API = init_with_api

		# Use a local dict instead of a remote one
		if not self.API:
			self.data = dict()

	# Allows for easier logging of update timing
	def updateData(self, key, data):
		# Write entry to main REST server
		if self.API:
			# Ignore speed and RPM / SPEED
			if key is not "RPM" and key is not "SPEED":
				r = requests.post(self.API+"/session/"+key, json={"value": str(data)}, headers={'Content-type': 'application/json', 'Accept': 'text/plain'})
				if r.status_code != 200:
					logging.debug("Failed to POST data to API: "+r.reason)
		else:
			self.data[key] = data

	# Checks for any external messages sent to socket,
	def checkExternalMessages(self):
		# Write entry to main REST server
		if self.API:
			r = requests.get(self.API+"/pybus/queue")
			if r.status_code == 200:
				message = r.json()
				if message != "{}":
					logging.info("Got External Message: {}".format(message))
				return message
			else:
				logging.debug("Failed to POST data to API: "+r.reason)