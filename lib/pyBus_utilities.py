############################################################################
# UTILITY FUNCTIONS
# THESE ARE USED FOR INTERNAL OR EXTERNAL DIRECTIVES, 
# OFTEN COMBINING SEVERAL IBUS WRITES INTO ONE FUNCTION
#
# TYPICALLY DIRECTIVES ARE REACTIVE, THESE UTLITIES ARE ACTIVE
############################################################################

import requests
import pyBus_eventDriver as main
import pyBus_directives as directives

# Emulates pressing the "MODE" button on stereo
# Very useful for changing back to AUX input without using the stock radio
def pressMode():
	# If you're switching to radio, 
	# prepare to be spammed with Radio station song/artist/location/signal strength packets.
	# This will probably freeze the WRITER for 10+ seconds
	main.WRITER.writeBusPacket('F0', '68', ['48', '23']) # push
	main.WRITER.writeBusPacket('F0', '68', ['48', 'A3']) # release

# Press number pad, 1-6
# On radio this will switch to that assigned station
# On aux this will adjust the gain
def pressNumPad(number=6):
	if(number == 1):
		main.WRITER.writeBusPacket('F0', '68', ['48', '11']) # push
		main.WRITER.writeBusPacket('F0', '68', ['48', '91']) # release
	elif(number == 2):
		main.WRITER.writeBusPacket('F0', '68', ['48', '01']) # push
		main.WRITER.writeBusPacket('F0', '68', ['48', '81']) # release
	elif(number == 3):
		main.WRITER.writeBusPacket('F0', '68', ['48', '12']) # push
		main.WRITER.writeBusPacket('F0', '68', ['48', '92']) # release
	elif(number == 4):
		main.WRITER.writeBusPacket('F0', '68', ['48', '02']) # push
		main.WRITER.writeBusPacket('F0', '68', ['48', '82']) # release
	elif(number == 5):
		main.WRITER.writeBusPacket('F0', '68', ['48', '13']) # push
		main.WRITER.writeBusPacket('F0', '68', ['48', '93']) # release
	elif(number == 6):
		main.WRITER.writeBusPacket('F0', '68', ['48', '03']) # push
		main.WRITER.writeBusPacket('F0', '68', ['48', '83']) # release

# Press number functions, for easy server access
def press1():
	pressNumPad(1)
def press2():
	pressNumPad(2)
def press3():
	pressNumPad(3)
def press4():
	pressNumPad(4)
def press5():
	pressNumPad(5)
def press6():
	pressNumPad(6)

# This switches to AM, I forget what pressing twice does
def pressAM():
	main.WRITER.writeBusPacket('F0', '68', ['48', '21']) # push
	main.WRITER.writeBusPacket('F0', '68', ['48', 'A1']) # release

# This switches to FM, I forget what pressing twice does
def pressFM():
	main.WRITER.writeBusPacket('F0', '68', ['48', '31']) # push
	main.WRITER.writeBusPacket('F0', '68', ['48', 'B1']) # release

# Presses next button on Radio, changing stations or songs
def pressNext():
	main.WRITER.writeBusPacket('F0', '68', ['48', '00']) # push
	main.WRITER.writeBusPacket('F0', '68', ['48', '80']) # release

# Presses prev button on Radio, changing stations or songs
def pressPrev():
	main.WRITER.writeBusPacket('F0', '68', ['48', '10']) # push
	main.WRITER.writeBusPacket('F0', '68', ['48', '90']) # release

# Presses on the left dial, turning stereo on & off
def pressStereoPower():
	main.WRITER.writeBusPacket('F0', '68', ['48', '06']) # push
	main.WRITER.writeBusPacket('F0', '68', ['48', '86']) # release

def pressRecirculatingAir():
	main.WRITER.writeBusPacket('50', '5B', ['3A', '01']) # push
	main.WRITER.writeBusPacket('50', '5B', ['3A', '00']) # release

# Opens rear trunk
def openTrunk():
	main.WRITER.writeBusPacket('3F','00', ['0C', '02', '01'])
	main.SESSION.updateData("TRUNK_OPEN", True)

# VERY loud, careful
def turnOnAlarm():
	main.WRITER.writeBusPacket('3F', '00', ['0C', '00', '55'])

# Repeatedly flash low beam lights
def flashLowBeams():
	main.WRITER.writeBusPacket('00', 'BF', ['76', '04'])

# Repeatedly flash low beam lights and hazards
def flashLowBeamsAndHazards():
	main.WRITER.writeBusPacket('00', 'BF', ['76', '06'])

# Repeatedly flash high beam lights
def flashHighBeams():
	main.WRITER.writeBusPacket('00', 'BF', ['76', '08'])

# Repeatedly flash high beam lights and hazards
def flashHighBeamsAndHazards():
	main.WRITER.writeBusPacket('00', 'BF', ['76', '0A'])

# Repeatedly flash high beam lights and low beam lights
def flashHighBeamsAndLowBeams():
	main.WRITER.writeBusPacket('00', 'BF', ['76', '0C'])

# Repeatedly flash high beam lights and low beam lights and hazards
def flashAllExteriorLights():
	main.WRITER.writeBusPacket('00', 'BF', ['76', '0E'])

def turnOnHazards():
	main.WRITER.writeBusPacket('00', 'BF', ['76', '02'])

def turnOffAllExteriorLights():
	main.WRITER.writeBusPacket('00', 'BF', ['76', '00'])

def toggleInteriorLights():
	main.WRITER.writeBusPacket('3F', '00', ['0C', '01', '01'])

def toggleDoorLocks():
	main.WRITER.writeBusPacket('3F','00', ['0C', '34', '01'])

def lockDriverDoor():
	main.WRITER.writeBusPacket('3F','00', ['0C', '47', '01'])

def lockPassengerDoor():
	main.WRITER.writeBusPacket('3F','00', ['0C', '46', '01'])

def lockDoors():
	lockDriverDoor()
	lockPassengerDoor()
	directives.d_carLocked() # Trigger car locked function

def requestDoorStatus():
    main.WRITER.writeBusPacket('9C', '00', ['79'])

def requestIgnitionStatus():
    main.WRITER.writeBusPacket('00', '80', ['10'])

def requestLampStatus():
    main.WRITER.writeBusPacket('00', 'D0', ['5A'])

def requestTimeStatus():
	main.WRITER.writeBusPacket('A4', '80', ['41', '01', '01'])
	
def requestOdometer():
	main.WRITER.writeBusPacket('44', '03', ['80', '16', 'D1'])

def requestPDCStatus():
	main.WRITER.writeBusPacket('3F', '60', ['1B'])

def requestVehicleStatus():
	main.WRITER.writeBusPacket('80', 'D0', ['53'])

def requestTemperatureStatus():
	main.WRITER.writeBusPacket('D0', '80', ['1D'])

### Roll windows up about 40%
# Completely rolling up in one command is not possible
# Rolling up 100% can be achieved by popping up about 2.5 times (3)
def popWindowsUp():
	main.WRITER.writeBusPacket('3F','00', ['0C', '53', '01']) # Pop up window 1
	main.WRITER.writeBusPacket('3F','00', ['0C', '55', '01']) # Pop up window 2
	main.WRITER.writeBusPacket('3F','00', ['0C', '42', '01']) # Pop up window 3
	main.WRITER.writeBusPacket('3F','00', ['0C', '43', '01']) # Pop up window 3

### Roll windows down about 40%
# Completely rolling down in one command is not possible
# Rolling down 100% can be achieved by popping up about 2.5 times (3)
def popWindowsDown():
	main.WRITER.writeBusPacket('3F','00', ['0C', '52', '01']) # Pop down window 1
	main.WRITER.writeBusPacket('3F','00', ['0C', '54', '01']) # Pop down window 2
	main.WRITER.writeBusPacket('3F','00', ['0C', '41', '01']) # Pop down window 3
	main.WRITER.writeBusPacket('3F','00', ['0C', '44', '01']) # Pop down window 3

# Turns on the clown nose for 3 seconds
def turnOnClownNose():
	main.WRITER.writeBusPacket('3F', '00', ['0C', '4E', '01'])

# Not working, but seen in logs
# Put Convertible Top Down
def convertibleTopDown():
	# These are the 3 packets sent by the vert module
	# I realized these aren't directives, but rather progress updates
	# 0%, 50%, and 100% respectively
	#main.WRITER.writeBusPacket('9C', 'BF', ['7C', '00', '72'])
	#main.WRITER.writeBusPacket('9C', 'BF', ['7C', '04', '72'])
	#main.WRITER.writeBusPacket('9C', 'BF', ['7C', '08', '72'])
	pass

# Not working, but seen in logs
# Put Convertible Top Up
def convertibleTopUp():
	#main.WRITER.writeBusPacket('9C', 'BF', ['7C', '00', '71'])
	pass

# Tell IKE to set the time
def setTime(day, month, year, hour, minute):
	# Check inputs to make sure we don't break things:
	for c in [day, month, year, hour, minute]:
		if not isinstance(c, int) or c > 255 or c < 0:
			return False

	main.logging.info("Setting IKE time to {}/{}/{} {}:{}".format(day, month, year, hour, minute))

	# Write Hours : Minutes
	main.WRITER.writeBusPacket('3B', '80', ['40', '01', dec2hex(hour), dec2hex(minute)])
	# Write Day/Month/Year
	main.WRITER.writeBusPacket('3B', '80', ['40', '02', dec2hex(day), dec2hex(month), dec2hex(year[-2:4])])

	return True

#################################################################

def dec2hex(decimal):
    try:
        return  ('{:02x}'.format(decimal)).upper()
    except Exception, e:
        main.logging.error("Failed to convert "+decimal+" to hex. Is it formatted correctly?")
        main.logging.error(e)
        return False

def hex2bin(hexi):
    try:
        return bin(int(hexi, 16))[2:].zfill(len(hexi)*4)
    except Exception, e:
        main.logging.error("Failed to convert "+hexi+" to binary. Is it formatted correctly?")
        main.logging.error(e)
        return False

# Send command / request
def sendRequest(fetchURL):
	try:
		main.logging.debug(requests.get(fetchURL))
	except Exception, e:
		main.logging.debug("Failed to send GET request to "+fetchURL)
		main.logging.debug(e)

def getUtilities():
	return globals()