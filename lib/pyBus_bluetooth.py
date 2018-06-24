# Skeleton taken from https://gist.github.com/keithweaver/3d5dbf38074cee4250c7d9807510c7c3

import bluetooth, logging, subprocess

#####################################
# GLOBALS
#####################################
CONNECTION_LIST   = dict() # Init empty dict for monitoring and checking connections {MAC:socket?}
PHONE             = "4C:32:75:AD:98:24"

#####################################
# TODO : Error handling, esp for sockets
#        All BT media controls should check return of dbus for failures  
#

# Search nearby devices
def findNearbyDevices():
    global CONNECTION_LIST

    nearby_devices = bluetooth.discover_devices()
    for bdaddr in nearby_devices:
        logging.debug(str(bluetooth.lookup_name( bdaddr )) + " [" + str(bdaddr) + "]")
    
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

# Will attempt to skip current Track
def getMediaInfo(macAddr = PHONE):
    out, error = _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez", "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.freedesktop.DBus.Properties.Get", "string:org.bluez.MediaPlayer1", "string:Track"])
    return out

def getDeviceInfo(macAddr = PHONE):
    out, error = _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez", "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.freedesktop.DBus.Properties.Get", "string:org.bluez.MediaPlayer1", "string:Status"])
    return out

# Will attempt to skip current Track
def nextTrack(macAddr = PHONE):
    _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez", "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Next"])

# Will attempt to skip Track backwards
def prevTrack(macAddr = PHONE):
    _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez", "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Previous"])

# Checks for current pause / play status and toggles it
def togglePause(macAddr = PHONE):
    print(getDeviceInfo())

# Will attempt to pause playing media
def pause(macAddr = PHONE):
    _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez", "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Pause"])

# Will attempt to play media
def play(macAddr = PHONE):
    _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez", "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Play"])

# Quick utility function to run a subprocess and return 
def _runSubprocess(command):
    try:
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
    for p in message.split():
        for q in p.split('=:'):
            if len(q):
                jsonDict[q[0]] = q[1]

    logging.debug("DBUS message: {}".format(jsonDict))
    return jsonDict    

if __name__ == "__main__":
    findNearbyDevices()
    togglePause()