# Skeleton taken from https://gist.github.com/keithweaver/3d5dbf38074cee4250c7d9807510c7c3

import bluetooth, logging, subprocess

#####################################
# GLOBALS
#####################################
PORT              = 4890 # Port number used for bluetooth RFCOMM
CONNECTION_LIST   = dict() # Init empty dict for monitoring and checking connections {MAC:socket?}
CLIENT            = False # Default to server
SERVER_SOCK       = None # will be filled with socket object if above is true
PHONE             = "4C:32:75:AD:98:24"

#####################################

##
# TODO : Error handling, esp for sockets
##

# Open socket for recieving message
def receiveMessages():
    global SERVER_SOCK, CLIENT
    CLIENT = True # show we're the client for better management

    SERVER_SOCK=bluetooth.BluetoothSocket( bluetooth.RFCOMM )
    SERVER_SOCK.bind(("", PORT))
    SERVER_SOCK.listen(1)
    client_sock,address = SERVER_SOCK.accept()
    logging.debug("Accepted connection from " + str(address))

    # Repeatedly accept data from server
    while True:
        data = client_sock.recv(1024)
        logging.debug("received [%s]" % data)
        yield data

    client_sock.close()

# Send a message to a MAC address
def sendMessage(targetBluetoothMacAddress, message):
    global CONNECTION_LIST
    return # for now
    
    # Add to our master list if new MAC address
    if(targetBluetoothMacAddress not in CONNECTION_LIST.keys()):
        sock = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
        sock.connect((targetBluetoothMacAddress, PORT))
        CONNECTION_LIST[targetBluetoothMacAddress] = sock
    else:
        sock = CONNECTION_LIST[targetBluetoothMacAddress] # Fetch from list otherwise

    sock.send(message)

# Search nearby devices
def findNearbyDevices():
    global CONNECTION_LIST
    '''
    nearby_devices = bluetooth.discover_devices()
    for bdaddr in nearby_devices:
        logging.debug(str(bluetooth.lookup_name( bdaddr )) + " [" + str(bdaddr) + "]")
    
    # Update our master list of nearby devices, cleanup clients that have disconnected
    for bdaddr in CONNECTION_LIST.keys():
        if bdaddr not in nearby_devices:
            CONNECTION_LIST[bdaddr].close()
            CONNECTION_LIST[bdaddr] = False
    '''

# Quick check for a specific MAC address
def isNearby(macAddr):
    return (macAddr in CONNECTION_LIST and CONNECTION_LIST[macAddr] is not False)

# Check for connected BT device to Lucio
def isConnected(macAddr):
    return False

####
# TODO: All BT media controls should check return of dbus for failures
####

# Will attempt to skip current Track
def getMediaInfo(macAddr = PHONE):
    out, error = _runSubprocess("dbus-send --system --print-reply --type=method_call --dest=org.bluez /org/bluez/hci0/dev_{}/player0 org.freedesktop.DBus.Properties.Get string:org.bluez.MediaPlayer1 string:Track".format(macAddr.replace(':', '_')))
    return out

def getDeviceInfo(macAddr = PHONE):
    out, error = _runSubprocess("dbus-send --system --print-reply --type=method_call --dest=org.bluez /org/bluez/hci0/dev_{}/player0 org.freedesktop.DBus.Properties.Get string:org.bluez.MediaPlayer1 string:Status".format(macAddr.replace(':', '_')))
    return out

# Will attempt to skip current Track
def nextTrack(macAddr = PHONE):
    _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez", "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Next"])

# Will attempt to skip Track backwards
def prevTrack(macAddr = PHONE):
    _runSubprocess(["dbus-send", "--system", "--print-reply", "--type=method_call", "--dest=org.bluez", "/org/bluez/hci0/dev_{}/player0".format(macAddr.replace(':', '_')), "org.bluez.MediaPlayer1.Previous"])

# Will attempt to pause playing media
def pause(macAddr = PHONE):
    _runSubprocess("dbus-send --system --print-reply --type=method_call --dest=org.bluez /org/bluez/hci0/dev_{}/player0 org.bluez.MediaPlayer1.Pause".format(macAddr.replace(':', '_')))

# Will attempt to play media
def play(macAddr = PHONE):
    _runSubprocess("dbus-send --system --print-reply --type=method_call --dest=org.bluez /org/bluez/hci0/dev_{}/player0 org.bluez.MediaPlayer1.Play".format(macAddr.replace(':', '_')))

# Shuts down the bluetooth sockets if necessary
def shutdownBT():
    if CLIENT:
        SERVER_SOCK.close()
    else:
        # We're server, close off connections to clients
        for sock in CONNECTION_LIST.values():
            if sock:
                sock.close()

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
    print("Dbus message: {}".format(message))
    return message    

if __name__ == "__main__":
    findNearbyDevices()
    nextTrack()
    shutdownBT()