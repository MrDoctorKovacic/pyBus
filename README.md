# I'm archiving this fork in favor of my more streamlined Go port [gokbus](https://github.com/qcasey/gokbus)

I-BUS interface for my E46 BMW written in Python 2.7. BMW's I-BUS (DE: K-BUS) is a proprietary serial communication line similar to CAN, but used primarily for exchanges between "non-essential" modules like A/C or radio. [Here's a great writeup.](https://curious.ninja/blog/arduino-bmw-i-bus-interface-technical-details/) 

## Overview
* USB serial interface can be acquired from [Reslers.de](http://www.reslers.de/IBUS/). Other USB interfaces should work just as well, although are untested. 
* Communicates on the I-BUS to send and receive diagnostics, running status, button presses, vehicle info, etc. 
* Can map steering wheel controls to various functions. 
* Can listen for and subsequently run external directives/utilities. (Unlocking the car from your phone, for example) 
### Warning
K/I-BUS issues can be difficult to diagnose and fix, so please don't use this to mess up your car. Each E46 sends different bus packets depending on the car's year and configuration. This likely won't be plug & play.

## Pre-Requisites
* python & python-setuptools 
	* `sudo apt-get install python python-setuptools`
* pyserial & requests
	* `pip install pyserial requests` 

## Optional Features
* **[MDroid-Core](https://github.com/MrDoctorKovacic/MDroid-Core)** (defined by --with-api) is a REST interface allowing time-series logging, Bluetooth control, and receiving commands from an external interface. It also makes logging other data such as OBD or GPS pretty seamless.

*Note: this branch has been slashed of features. I wanted to avoid a one-size-fits-all program since growing requirements will make this unwieldy. This is now first and foremost an I-BUS interface.*

* **More Native Features** including Bluetooth, MySQL logging, and remote files can be found on [an earlier branch](https://github.com/MrDoctorKovacic/pyBus/tree/soylentspaghetti). 

## Quick Start
* Install the prerequisites above 
* Plug in iBus USB device 
* Run: `./pyBus.py --device <PATH to USB Device>` 
	* E.g. `./pyBus.py --device /dev/ttyUSB0` 

## Advanced Usage
`./pyBus.py --device <PATH to USB Device> --with-api http://localhost:5353 --with-session <PATH to session file>` 

## A Longer Drive
The meat and potatoes lie in pyBus_eventDriver.py - in there you'll find a large list of both **Directives** and **Utilities**. Generally speaking Directives are *reactive*, defining what happens when the interface reads specific activity. Utilities meanwhile are *active*, and are designed to emulate specific functions. 

For example: when running this hypothetical directive (which calls a utility), we'd run in an endless loop:
```python 
# openTrunk would emulate the car, and the interface would subsequently read d_trunkOpen
d_trunkOpen(packet):
	openTrunk()
```

Utilities can be used for doing things in addition to the car's normal function. Mind you, we can never completely remap.
```python 
# Will skip media backwards AND put the convertible top down
d_steeringPrev(packet):
	convertibleTopDown()
```

With Utilities and Directives we have a competent system for both logging and executing the car's various functions.

### Useful links
http://web.archive.org/web/20041204074622/www.openbmw.org/bus/  
http://web.comhem.se/bengt-olof.swing/ibusdevicesandoperations.htm   
http://www.online-rubin.de/BMW/I-Bus/I-BUS%20Codes%20e46.htm 
