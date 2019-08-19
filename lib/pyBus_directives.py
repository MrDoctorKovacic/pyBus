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
			'1100' 	 : 'd_ignitionOff', # Engine off
			'7202'	 : None, # Key, no button pressed (released)
			'7212'   : 'd_carLocked', # Locked via key
			'7222'	 : 'd_carUnlocked', # Unlocked via key
			'7A'	 : 'd_windowDoorMessage', # Response to window / door status request
			'7D0000' : 'd_topClosed', # Technically 'sunroof locked', but responds when top closed
			'7D00'	 : 'd_topOpen' # Last packet is the state / progress of open
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
		'80' : {
			'16' : None, # Odometer request
		},
		'BF' : { # Global
			'7404' : 'd_keyDetected', # Last byte is key #
			'740500' : 'd_keyIn', # Key in, to 2nd position
			'7401FF' : 'd_keyOut', # No_key_detected - Triggred by pulling the key out
			'7400FF' : 'd_keyNotDetected', # No_key_detected - Triggered in response to a request
			#'7400' : 'd_keyIn',
			#'7A' : 'd_windowDoorMessage'
		}
	},
	'50' : { # MF Steering Wheel Buttons
		'5B' : {
			'3A01' : None, # AUC - recirculating air pressed
			'3A00' : None, # AUC - recirculating air released
		},
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
	'72' : {
		'BF' : {
			'780000' : 'd_seatMemory', # One of the seat memory buttons were pushed
			'780100' : 'd_seatMemory', # Button 1 released
			'780200' : 'd_seatMemory', # Button 2 released
			'780400' : 'd_seatMemory', # Button 3 released
		}
	},
	'80' : {
		'68' : { # Radio buttons
			'31000007' : 'd_cdNext', # Seek > pressed
			'31000047' : None, # Seek > released
			'31000006' : 'd_cdPrev', # Seek < pressed
			'31000046' : None, # Seek < released
			'31000009' : None, # FM pressed
			'31000049' : None, # FM released
			'3100000A' : None, # AM pressed
			'3100004A' : None, # AM released
			'3100000C' : None, # MAN pressed
			'3100004C' : None, # MAN released
			'3100000E' : None, # SC/RP pressed
			'3100004E' : None, # SC/RP released
		},
		'BF' : {
			'0201'  : None, # Device status ready after Reset
			'OTHER' : 'd_custom_IKE' # Use ALL to send all data to a particular function
		},
		'E7' : {
			'2A0000' : 'd_auxHeatingOff' # NAVCODER - Not totally sure what this refers to ('Aux_Heating_LED = Off')
		}
	},
	'9C' : { # Technically Sunroof module, operates w/ convertible tops
		'BF' : {
			'7C0174' : 'd_topClosed',
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
		'80' : { # Vehicle Data, in response to request
			'ALL' : 'd_vehicleData'
		},
		'BF' : {
			'5B6100040001' : None, # lights turned on (including interior)
			'5B0100000001' : None, # lights turned off (including interior)
			'5B6000040000' : None # Indicator_Left Indicator_Right Indicator_sync  All_OK
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

def d_ignitionOff(packet):
	main.SESSION.updateData("ENGINE", False)

def d_keyDetected(packet):
	main.SESSION.updateData("KEY_DETECTED", True)
	main.SESSION.updateData("LAST_KEY_USED", packet['dat'][-1])

def d_keyNotDetected(packet):
	main.SESSION.updateData("KEY_DETECTED", False)

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

# If sunroof / convertible top is closed
def d_topClosed(packet):
	main.SESSION.updateData("CONVERTIBLE_TOP_OPEN", False)

# Called when sunroof / convertible top is open. Last packet is state / progress of opening
def d_topOpen(packet):
	main.SESSION.updateData("CONVERTIBLE_TOP_OPEN", True)
	main.SESSION.updateData("CONVERTIBLE_TOP_PROGRESS", packet['dat'][-1])

# Whatever aux heating is
def d_auxHeatingOff(packet):
	main.SESSION.updateData("AUX_HEATING", False)

# Called when driver seat memory buttons are pushed
def d_seatMemory(packet):
	if packet['dat'][1] == "00":
		main.SESSION.updateData("SEAT_MEMORY_PUSHED", True)
	else:
		if packet['dat'][1] == "01": seatMemory = "SEAT_MEMORY_1"
		elif packet['dat'][1] == "02": seatMemory = "SEAT_MEMORY_2"
		elif packet['dat'][1] == "04": seatMemory = "SEAT_MEMORY_3"

		if main.SESSION.data["SEAT_MEMORY_PUSHED"]:
			main.SESSION.updateData("SEAT_MEMORY_PUSHED", False)
			main.SESSION.updateData(seatMemory, True)

# Called when doors are locked.
def d_carLocked(packet = None):
	main.SESSION.updateData("DOOR_LOCKED_DRIVER", True)
	main.SESSION.updateData("DOOR_LOCKED_PASSENGER", True)
	main.SESSION.updateData("DOORS_LOCKED", True)

# Called when ALL doors are unlocked.
def d_carUnlocked(packet = None):
	main.SESSION.updateData("DOOR_LOCKED_DRIVER", False)
	main.SESSION.updateData("DOOR_LOCKED_PASSENGER", False)
	main.SESSION.updateData("DOORS_LOCKED", False)

# Called when ONLY passenger door is locked
# This isn't very often, especially on coupe models
def d_passengerDoorLocked(packet):
	main.SESSION.updateData("DOOR_LOCKED_PASSENGER", True)
	if "DOOR_LOCKED_DRIVER" in main.SESSION.data and main.SESSION.data["DOOR_LOCKED_DRIVER"]:
		main.SESSION.updateData("DOORS_LOCKED", True)

# Called when ONLY DRIVER door is locked
# This isn't very often, especially on coupe models
def d_driverDoorLocked(packet):
	main.SESSION.updateData("DOOR_LOCKED_DRIVER", True)
	if "DOOR_LOCKED_PASSENGER" in main.SESSION.data and main.SESSION.data["DOOR_LOCKED_PASSENGER"]:
		main.SESSION.updateData("DOORS_LOCKED", True)

# This packet is used to parse all messages from the IKE (instrument control electronics), as it contains speed/RPM info. 
# But the data for speed/rpm will vary, so it must be parsed via a method linked to 'ALL' data in the JSON DIRECTIVES
def d_custom_IKE(packet):
	packetData = packet['dat']

	# Ignition Status
	if packetData[0] == '11':
		if (packetData[1] == '00'): # Key Out.
			main.SESSION.updateData("KEY_STATE", False)
		elif (packetData[1] == '01'): # Pos 1
			main.SESSION.updateData("KEY_STATE", "POS_1")
		elif (packetData[1] == '03'): # Pos 2
			main.SESSION.updateData("KEY_STATE", "POS_2")
		elif (packetData[1] == '07'): # Start
			main.SESSION.updateData("KEY_STATE", "START")

	# Sensor Status, broadcasted every 10 seconds
	elif packetData[0] == '13':
		# Haven't decoded this one yet
		if packetData.join('') == "1303000000000014":
			main.SESSION.updateData("HANDBRAKE", True)
			main.SESSION.updateData("OIL_PRESSURE", "LOW")

		main.SESSION.updateData("IKE_SENSOR_STATUS", (packetData[1]+packetData[2]+packetData[3]+packetData[4]+packetData[5]+packetData[6]+packetData[7]))

		# Byte 7 holds temp in c
		main.SESSION.updateData("OUTSIDE_TEMP_2", int(packetData[7], 16))

	# Odometer reading, in response to request
	elif packetData[0] == '17':
		main.SESSION.updateData("ODOMETER", int(packetData[3]+packetData[2]+packetData[1], 16))

	# Speed / RPM Info, broadcasted every 2 seconds
	elif packetData[0] == '18':
		speed = int(packetData[1], 16) * 2
		revs = int(packetData[2], 16)

		main.SESSION.updateData("SPEED", speed)
		main.SESSION.updateData("RPM", revs*100)

	# Temperature Status, broadcasted every 10 seconds
	elif packetData[0] == '19':
		main.SESSION.updateData("OUTSIDE_TEMP", int(packetData[1], 16))
		main.SESSION.updateData("COOLANT_TEMP", int(packetData[2], 16))

		# Only for european models I believe, or if you've set this to be tracked with INPA/NCS. Otherwise 0
		main.SESSION.updateData("OIL_TEMP", int(packetData[3], 16))

	# OBC Estimated Range / Average Speed
	elif packetData[0] == '24':
		if (packetData[1] == '06'):
			main.SESSION.updateData("RANGE_KM", int((packetData[3]+packetData[4]+packetData[5]+packetData[6]), 16))
		elif (packetData[1] == '0A'):
			main.SESSION.updateData("AVG_SPEED", int((packetData[3]+packetData[4]+packetData[5]+packetData[6]), 16))

# Handles Vehicle data, like VIN and service info
def d_vehicleData(packet):
	packetData = packet['dat']

	if packetData[0] == 54 and len(packet >= 14):
		# VIN number is in plaintext, first two model letters are ASCII
		main.SESSION.updateData("VIN", (packetData[1].decode('hex')+packetData[2].decode('hex')+packetData[3]+packetData[4]+packetData[5][0]))

		# Odometer, rounded to the nearest hundred in KM
		main.SESSION.updateData("ODOMETER_ESTIMATE", 100*int((packetData[6]+packetData[7]), 16))

		# Liters since last service, first byte and first 4 bits in second byte
		# I.E. '58 02' would be 88+0 or 880 liters
		main.SESSION.updateData("LITERS_SINCE_LAST_SERVICE", str(int((packetData[9]), 16))+str(int((packetData[10][0]), 16)))

		# Days since last service
		main.SESSION.updateData("DAYS_SINCE_LAST_SERVICE", int((packetData[12]+packetData[13]), 16))

# Handles messages sent when door/window status changes
# binary 1 if open, 0 if closed
def d_windowDoorMessage(packet):
	packetData = packet['dat']
	doorByte = utils.hex2bin(packetData[1])
	windowByte = utils.hex2bin(packetData[2])

	if doorByte[2]: d_carLocked()
	if doorByte[3]: d_carUnlocked()

	# Bits 4 and 5 are likely rear passenger / rear driver door respectively 
	# Unused in coupes / convertibles obviously
	if doorByte[6]: main.SESSION.updateData("DOOR_OPEN_PASSENGER", True)
	else: main.SESSION.updateData("DOOR_OPEN_PASSENGER", False)

	if doorByte[7]: main.SESSION.updateData("DOOR_OPEN_DRIVER", True)
	else: main.SESSION.updateData("DOOR_OPEN_DRIVER", False)

	if windowByte[1]: main.SESSION.updateData("HOOD_OPEN", True)
	else: main.SESSION.updateData("HOOD_OPEN", False)

	if windowByte[4]: main.SESSION.updateData("WINDOW_OPEN_PASSENGER_REAR", True)
	else: main.SESSION.updateData("WINDOW_OPEN_PASSENGER_REAR", False)

	if windowByte[5]: main.SESSION.updateData("WINDOW_OPEN_DRIVER_REAR", True)
	else: main.SESSION.updateData("WINDOW_OPEN_DRIVER_REAR", False)

	if windowByte[6]: main.SESSION.updateData("WINDOW_OPEN_PASSENGER_FRONT", True)
	else: main.SESSION.updateData("WINDOW_OPEN_PASSENGER_FRONT", False)

	if windowByte[7]: main.SESSION.updateData("WINDOW_OPEN_DRIVER_FRONT", True)
	else: main.SESSION.updateData("WINDOW_OPEN_DRIVER_FRONT", False)

	# Re-evaluate aggregate window / door data
	meta_evalWindowDoor()


# Handles Rain/Light sensor data.
def d_rainLightSensor(packet):
	packetData = packet['dat']

	if packetData[0] == '59':
		# Decode first packet (reason)
		if packetData[2] == '01':
			main.SESSION.updateData("LIGHT_SENSOR_REASON", "TWILIGHT")
		elif packetData[2] == '02':
			main.SESSION.updateData("LIGHT_SENSOR_REASON", "DARKNESS")
		elif packetData[2] == '04':
			main.SESSION.updateData("LIGHT_SENSOR_REASON", "RAIN")
		elif packetData[2] == '08':
			main.SESSION.updateData("LIGHT_SENSOR_REASON", "TUNNEL")
		elif packetData[2] == '10':
			main.SESSION.updateData("LIGHT_SENSOR_REASON", "BASEMENT_GARAGE")

		# Decode second nibble of second packet (on / off)
		if packetData[1][1] == '1':
			main.SESSION.updateData("LIGHT_SENSOR_ON", True)
		elif packetData[1][1] == '0':
			main.SESSION.updateData("LIGHT_SENSOR_ON", False)

		# Decode first nibble of second packet (intensity)
		main.SESSION.updateData("LIGHT_SENSOR_INTENSITY", packetData[1][0])

	main.SESSION.updateData("RAIN_LIGHT_SENSOR_STATUS", (''.join(packet['dat'])))

# Handles raw climate control (Integrated Heating And Air Conditioning) data
def d_climateControl(packet):
	packetData = ''.join(packet['dat'])

	if(packetData == "830000"):
		main.SESSION.updateData("AIR_CONDITIONING_ON", False)
	elif(packetData == "838008"):
		main.SESSION.updateData("AIR_CONDITIONING_ON", True)
	else: 
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

############################################################################
# META FUNCTIONS
# Helps combine different directives
############################################################################

# Re-evaluate aggregate window / door data
def meta_evalWindowDoor():
	# check for nil values first, should not eval those as false
	if main.SESSION.data["DOOR_OPEN_PASSENGER"] is not None and main.SESSION.data["DOOR_OPEN_DRIVER"] is not None:
		if not main.SESSION.data["DOOR_OPEN_PASSENGER"] and not main.SESSION.data["DOOR_OPEN_DRIVER"]:
			main.SESSION.updateData("DOORS_OPEN", False)
		else:
			main.SESSION.updateData("DOORS_OPEN", True)

	if (main.SESSION.data["WINDOW_OPEN_DRIVER_FRONT"] is not None 
	and main.SESSION.data["WINDOW_OPEN_DRIVER_REAR"] is not None 
	and main.SESSION.data["WINDOW_OPEN_PASSENGER_FRONT"] is not None 
	and main.SESSION.data["WINDOW_OPEN_PASSENGER_REAR"] is not None):
		if (not main.SESSION.data["WINDOW_OPEN_DRIVER_FRONT"] 
		and not main.SESSION.data["WINDOW_OPEN_DRIVER_REAR"] 
		and not main.SESSION.data["WINDOW_OPEN_PASSENGER_FRONT"] 
		and not main.SESSION.data["WINDOW_OPEN_PASSENGER_REAR"]):
			main.SESSION.updateData("WINDOWS_OPEN", False)
		else:
			main.SESSION.updateData("WINDOWS_OPEN", True)

def getDirectives():
	return globals()