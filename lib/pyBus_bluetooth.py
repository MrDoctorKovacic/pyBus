# Skeleton taken from https://gist.github.com/keithweaver/3d5dbf38074cee4250c7d9807510c7c3

import bluetooth
import logging
import subprocess

#####################################
# GLOBALS
#####################################
# Default address of phone/media device to connect on startup
PHONE = None

#####################################

# Connect a bluetooth device, typically run at startup
def connect(macAddr=PHONE):
	out, error = _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez",
								"/org/bluez/hci0/dev_{}".format(macAddr.replace(':', '_')), "org.bluez.Device1.Connect"], runInBackground=True)
	_runSubprocess(["/usr/local/bin/a2dp-agent"], runInBackground=True)
	if error:
		logging.error("Error when running connect dbus command: {}".format(error))
	return out

# Will attempt to skip current Track
def getMediaInfo(macAddr=PHONE):
	out, error = _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez", "/org/bluez/hci0/dev_{}/player0".format(
		macAddr.replace(':', '_')), "org.freedesktop.DBus.Properties.Get", "string:org.bluez.MediaPlayer1", "string:Track"])
	if error:
		logging.error("Error when running getMediaInfo dbus command: {}".format(error))
	return out

def getDeviceInfo(macAddr=PHONE):
	out, error = _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez", "/org/bluez/hci0/dev_{}/player0".format(
		macAddr.replace(':', '_')), "org.freedesktop.DBus.Properties.Get", "string:org.bluez.MediaPlayer1", "string:Status"])
	if error:
		logging.error("Error when running getDeviceInfo dbus command: {}".format(error))
	return out

# Will attempt to skip current Track
def nextTrack(macAddr=PHONE):
	out, error = _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez",
				   "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Next"])
	if error:
		logging.error("Error when running nextTrack dbus command: {}".format(error))
	return out

# Will attempt to skip Track backwards
def prevTrack(macAddr=PHONE):
	out, error = _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez",
				   "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Previous"])
	if error:
		logging.error("Error when running prevTrack dbus command: {}".format(error))
	return out

# Checks for current pause / play status and toggles it
def togglePause(macAddr=PHONE):
	return getDeviceInfo()

# Will attempt to pause playing media
def pause(macAddr=PHONE):
	out, error = _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez",
				   "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Pause"])
	if error:
		logging.error("Error when running pause dbus command: {}".format(error))
	return out

# Will attempt to play media
def play(macAddr=PHONE):
	out, error= _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez",
				   "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Play"])
	if error:
		logging.error("Error when running play dbus command: {}".format(error))
	return out

# Will attempt to play media after a short delay
def playDelayed(macAddr=PHONE):
	_runSubprocess(["sleep 1 && dbus-send --system --print-reply --type=method_call --dest=org.bluez /org/bluez/hci0/dev_{}/player0 org.bluez.MediaPlayer1.Play".format(macAddr.replace(':', '_'))], runInBackground=True)

# Quick utility function to run a subprocess and return
def _runSubprocess(command, runInBackground=False):
	try:
		if runInBackground:
			subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
		else:
			process = subprocess.Popen(command, stdout=subprocess.PIPE)
			out, err = process.communicate()
			return [_parseDBusReply(out), _parseDBusReply(err)]
	except Exception, e:
		logging.error("Failed to run the following process: {}\nRaised: {}".format(command, e))
		return False

# Parse the formatting of the dbus return value into JSON
def _parseDBusReply(message):
	jsonDict = dict()
	if message:
		for p in message.split():
			for q in p.split('=:'):
				if len(q):
					jsonDict[q[0]] = q[1]

	logging.info("DBUS message: {}".format(jsonDict))
	return jsonDict