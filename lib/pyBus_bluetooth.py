# Skeleton taken from https://gist.github.com/keithweaver/3d5dbf38074cee4250c7d9807510c7c3

import bluetooth
import logging
import subprocess

#####################################
# GLOBALS
#####################################
# Init empty dict for monitoring and checking connections {MAC:socket?}
CONNECTION_LIST = dict()
# Default address of phone/media device to connect on startup
PHONE = "4C:32:75:AD:98:24"

#####################################
# TODO : Error handling, esp for sockets
#        All BT media controls should check return of dbus for failures
#

# Search nearby devices
def findNearbyDevices():
    global CONNECTION_LIST

    nearby_devices = bluetooth.discover_devices()
    for bdaddr in nearby_devices:
        logging.debug(str(bluetooth.lookup_name(bdaddr)) +
                      " [" + str(bdaddr) + "]")

    # Update our master list of nearby devices, cleanup clients that have disconnected
    for bdaddr in CONNECTION_LIST.keys():
        if bdaddr not in nearby_devices:
            CONNECTION_LIST[bdaddr].close()
            CONNECTION_LIST[bdaddr] = False

# Quick check for a specific MAC address
def isNearby(macAddr):
    return (macAddr in CONNECTION_LIST and CONNECTION_LIST[macAddr] is not False)

# Check for connected BT device to Lucio
def isConnected(macAddr):
    return False

# Connect a bluetooth device, typically run at startup
def connect(macAddr=PHONE):
	out, error = _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez",
	                            "/org/bluez/hci0/dev_{}".format(macAddr.replace(':', '_')), "org.bluez.Device1.Connect"])
	_runSubprocess(["/usr/local/bin/a2dp-agent"], runInBackground=True)
	return out

# Will attempt to skip current Track
def getMediaInfo(macAddr=PHONE):
    out, error = _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez", "/org/bluez/hci0/dev_{}/player0".format(
        macAddr.replace(':', '_')), "org.freedesktop.DBus.Properties.Get", "string:org.bluez.MediaPlayer1", "string:Track"])
    return out


def getDeviceInfo(macAddr=PHONE):
    out, error = _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez", "/org/bluez/hci0/dev_{}/player0".format(
        macAddr.replace(':', '_')), "org.freedesktop.DBus.Properties.Get", "string:org.bluez.MediaPlayer1", "string:Status"])
    return out

# Will attempt to skip current Track
def nextTrack(macAddr=PHONE):
    _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez",
                   "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Next"])

# Will attempt to skip Track backwards
def prevTrack(macAddr=PHONE):
    _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez",
                   "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Previous"])

# Checks for current pause / play status and toggles it
def togglePause(macAddr=PHONE):
    return getDeviceInfo()

# Will attempt to pause playing media
def pause(macAddr=PHONE):
    _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez",
                   "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Pause"])

# Will attempt to play media
def play(macAddr=PHONE):
    _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez",
                   "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Play"])

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
        logging.error("Failed to run command: {}".format(command))
        logging.error(e)
        return False

# Parse the formatting of the dbus return value into JSON
def _parseDBusReply(message):
    jsonDict = dict()
    if message:
		for p in message.split():
			for q in p.split('=:'):
				if len(q):
					jsonDict[q[0]] = q[1]

    logging.debug("DBUS message: {}".format(jsonDict))
    return jsonDict    

if __name__ == "__main__":
    findNearbyDevices()
    togglePause()