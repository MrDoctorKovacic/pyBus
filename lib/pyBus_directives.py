import pyBus_eventDriver as main
import pyBus_utilities as utils

#####################################
# GLOBALS
#####################################
# directives list - maps function to src:dest:data
# first level of directives is filtering the src, so put in the integer representation of the src
# second level is destination
# third level is data : function name
LIST = {
	'00' : {
		'BF' : {
			'0200B9' : 'd_carUnlocked', # Unlocked via key
			'7212DB' : 'd_carLocked', # Locked via key
			#'7A1000' : None, # passenger door opened, probably
			'7A1203' : None, # passenger door opened, probably
			'7A5203' : None, # passenger door opened, probably
			#'7A5202' : None, # passenger door closed, probably
			'7A5003' : None, # passenger door closed
			'7A1003' : None, # passenger door closed, probably
			'7A5020' : None, # driver window popped up after closing door
			'7A5021' : None, # driver door closed
			'7A5120' : None, # driver window popped down before opening door
			'7A5121' : None, # driver door opened
			'7A1000' : 'd_carUnlocked', # Doors unlocked (from console button)
			'7A2000' : 'd_carLocked', # Doors unlocked (from console button)
		}
	},
	'3F' : {
		'00' : {
			''
			'0C3401' : 'd_carUnlocked', # All doors unlocked
			'0C4601' : 'd_passengerDoorLocked',
			'0C4701' : 'd_driverDoorLocked',
			'OTHER'  : 'd_diagnostic'
		}
	},
	'44' : { # EWS Ignition / Immobilizer
		'BF' : { # Global
			'740400' : None, # Toggle key in/out?
			'740500' : 'd_keyIn', # Key in, to 2nd position
			'7401FF' : 'd_keyOut', # Triggred by pulling the key out
			'7400FF' : 'd_keyOut', # This is in response to a request
			#'7400' : 'd_keyIn',
			'7A' : 'd_windowDoorMessage'
		}
	},
	'50' : { # MF Steering Wheel Buttons
		'68' : { # RADIO
			'3210' : None, # Volume Down
			'3211' : None, # Volume Up
			'3B01' : 'd_steeringNext',
			'3B11' : None, # Next, long press
			'3B21' : None, # Next Released
			'3B08' : 'd_steeringPrev',
			'3B18' : None, # Prev, long press
			'3B28' : None # Prev Released
		},
		'C8' : {
			'01' : None, # This can happen via RT button or ignition
			'019A' : '', # RT button?
			'3B40' : None, # reset
			'3B80' : 'd_steeringSpeak', # Dial button
			'3B90' : 'd_steeringSpeakLong', # Dial button, long press
			'3BA0' : None # Dial button, released
		},
		'FF' : {
			'3B40' : 'd_steeringRT' # also RT Button?
		}
	},
	'5B' : {
		'80' : {
			'ALL' : 'd_climateControl'
		}
	},
	'68' : {
		'18' : {
			'01'     : '',
			'380000' : None, # d_cdSendStatus
			'380100' : None,
			'380300' : None,
			'380A00' : 'd_cdNext', # Next button on Radio
			'380A01' : 'd_cdPrev', # Prev button on Radio
			'380700' : None,
			'380701' : None,
			'380601' : None, # 1 pressed
			'380602' : None, # 2 pressed
			'380603' : None, # 3 pressed
			'380604' : None, # 4 pressed
			'380605' : None, # 5 pressed
			'380606' : None, # 6 pressed
			'380400' : None, # prev Playlist function?
			'380401' : None, # next Playlist function?
			'380800' : None,
			'380801' : None
		}
	},
	'80' : {
		'BF' : {
			'ALL' : 'd_custom_IKE' # Use ALL to send all data to a particular function
		}
	},
	'C0' : { # telephone module
		'80' : {  # IKE
			'234220' : 'd_steeringRT' # Telephone invoked (from steering wheel?)
		},
		'68' : {
			'3100000B' : None, # Mode button pressed
			'3100134B' : None, # Mode button released
		}
	},
	'D0' : {
		'BF' : {
			'5B6100040001' : None, # hazard lights turned on (including interior)
			'5B0100000001' : None # hazard lights turned off (including interior)
		}
	},
	'E8' : {
		'D0' : {
			'ALL' : 'd_rainLightSensor'
		}
	},
	'F0' : { # Board Monitor Buttons
		'68' : { # Radio
			'4806' : None # Radio power toggled

		}
	}
}

############################################################################
# FROM HERE ON ARE THE DIRECTIVES
# DIRECTIVES ARE WHAT I CALL SMALL FUNCTIONS WHICH ARE INVOKED WHEN A 
# CERTAIN CODE IS READ FROM THE IBUS.
#
# SO ADD YOUR OWN IF YOU LIKE, OR MODIFY WHATS THERE. 
# USE THE BIG JSON DICTIONARY AT THE TOP
############################################################################
# All directives should have a d_ prefix as we are searching GLOBALLY for function names.. so best have unique enough names
############################################################################

def d_keyOut(packet):
	main.SESSION.updateData("KEY_STATE", False)
	main.SESSION.updateData("RPM", 0)
	main.SESSION.updateData("SPEED", 0)
	if main.MEDIA_HOST: 
		utils.sendBluetoothCommand(main.MEDIA_HOST+"/bluetooth/disconnect")

def d_keyIn(packet):
	main.SESSION.updateData("KEY_STATE", True)
	if main.MEDIA_HOST: 
		utils.sendBluetoothCommand(main.MEDIA_HOST+"/bluetooth/connect")

# Called whenever doors are locked.
def d_carLocked(packet = None):
	main.SESSION.updateData("DOOR_LOCKED_DRIVER", True)
	main.SESSION.updateData("DOOR_LOCKED_PASSENGER", True)
	main.SESSION.updateData("DOORS_LOCKED", True)

# Called whenever ALL doors are unlocked.
def d_carUnlocked(packet = None):
	main.SESSION.updateData("DOOR_LOCKED_DRIVER", False)
	main.SESSION.updateData("DOOR_LOCKED_PASSENGER", False)
	main.SESSION.updateData("DOORS_LOCKED", False)

# Called whenever ONLY passenger door is locked
# This isn't very often, especially on coupe models
def d_passengerDoorLocked(packet):
	main.SESSION.updateData("DOOR_LOCKED_PASSENGER", True)
	if main.SESSION.data["DOOR_LOCKED_DRIVER"]:
		main.SESSION.updateData("DOORS_LOCKED", True)

# Called whenever ONLY DRIVER door is locked
# This isn't very often, especially on coupe models
def d_driverDoorLocked(packet):
	main.SESSION.updateData("DOOR_LOCKED_DRIVER", True)
	if main.SESSION.data["DOOR_LOCKED_PASSENGER"]:
		main.SESSION.updateData("DOORS_LOCKED", True)

# This packet is used to parse all messages from the IKE (instrument control electronics), as it contains speed/RPM info. 
# But the data for speed/rpm will vary, so it must be parsed via a method linked to 'ALL' data in the JSON DIRECTIVES
def d_custom_IKE(packet):
	packet_data = packet['dat']

	# Ignition Status
	if packet_data[0] == '11':
		if (packet_data[1] == '00'): # Key Out.
			main.SESSION.updateData("KEY_STATE", False)
		elif (packet_data[1] == '01'): # Pos 1
			main.SESSION.updateData("KEY_STATE", "POS_1")
		elif (packet_data[1] == '03'): # Pos 2
			main.SESSION.updateData("KEY_STATE", "POS_2")
		elif (packet_data[1] == '07'): # Start
			main.SESSION.updateData("KEY_STATE", "START")

	# Sensor Status, broadcasted every 10 seconds
	elif packet_data[0] == '13':
		main.SESSION.updateData("IKE_SENSOR_STATUS", (packet_data[1]+packet_data[2]+packet_data[3]+packet_data[4]+packet_data[5]+packet_data[6]+packet_data[7]))

		# Byte 7 holds temp in c
		main.SESSION.updateData("OUTSIDE_TEMP_2", int(packet_data[7], 16))

	# Speed / RPM Info, broadcasted every 2 seconds
	elif packet_data[0] == '18':
		speed = int(packet_data[1], 16) * 2
		revs = int(packet_data[2], 16)

		main.SESSION.updateData("SPEED", speed)
		main.SESSION.updateData("RPM", revs*100)

	# Temperature Status, broadcasted every 10 seconds
	elif packet_data[0] == '19':
		main.SESSION.updateData("OUTSIDE_TEMP", int(packet_data[1], 16))
		main.SESSION.updateData("COOLANT_TEMP", int(packet_data[2], 16))

		# Only for european models I believe, or if you've set this to be tracked with INPA/NCS. Otherwise 0
		main.SESSION.updateData("OIL_TEMP", int(packet_data[3], 16))

	# OBC Estimated Range / Average Speed
	elif packet_data[0] == '24':
		if (packet_data[1] == '06'):
			main.SESSION.updateData("RANGE_KM", int((packet_data[3]+packet_data[4]+packet_data[5]+packet_data[6]), 16))
		elif (packet_data[1] == '0A'):
			main.SESSION.updateData("AVG_SPEED", int((packet_data[3]+packet_data[4]+packet_data[5]+packet_data[6]), 16))

# Handles messages sent when door/window status changes
def d_windowDoorMessage(packet):
	main.SESSION.updateData("WINDOR_DOOR_STATUS", (''.join(packet['dat'])))

# Handles Rain/Light sensor data. TODO: find what light/dark is and wet/dry is
def d_rainLightSensor(packet):
	main.SESSION.updateData("RAIN_LIGHT_SENSOR_STATUS", (''.join(packet['dat'])))

# Handles raw climate control (Integrated Heating And Air Conditioning) data
def d_climateControl(packet):
	main.SESSION.updateData("CLIMATE_CONTROL_STATUS", (''.join(packet['dat'])))

# Handles any unknown diagnostic packets for logging
def d_diagnostic(packet):
	main.SESSION.updateData("DIAGNOSTIC", (''.join(packet['dat'])))

def d_togglePause(packet):
	if main.MEDIA_HOST: 
		utils.sendBluetoothCommand(main.MEDIA_HOST+"/bluetooth/pause")

def d_cdNext(packet):
	pass

def d_cdPrev(packet):
	pass

def d_steeringNext(packet):
	if main.MEDIA_HOST: 
		utils.sendBluetoothCommand(main.MEDIA_HOST+"/bluetooth/next")

def d_steeringPrev(packet):
	if main.MEDIA_HOST: 
		utils.sendBluetoothCommand(main.MEDIA_HOST+"/bluetooth/prev")

def d_steeringRT(packet):
	utils.pressMode()
	utils.pressNumPad(6) # Change gain to max, better audio over aux

def d_steeringSpeak(packet):
	utils.pressMode()

def d_steeringSpeakLong(packet):
	pass