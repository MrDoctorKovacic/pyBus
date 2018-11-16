pyBus
=====
### Forked from ezeakeal's excellent [pyBus](https://github.com/ezeakeal/pyBus)

iBus interface for my E46 BMW written in Python. I'm using it for a backend to a Nexus 7 install, if you want more of a factory integration I recommend one of the other forks. 
This is to be used with the USB interface which can be acquired from [Reslers.de](http://www.reslers.de/IBUS/). Other USB interfaces should work just as well, although are untested. 

## Overview
* Interfaces with the BMW iBus to send and receive button presses, status changes, vehicle info, etc. 
* Records the car's state and keeps a running log that can be saved to disk and MySQL. 
* Can map steering wheel controls to a paired Bluetooth media player. 
* Can listen for external requests for functions to be run. (Unlocking the car from your phone, for example) 

### Warning
All software is in early alpha stages! K/I-Bus issues can be painful to diagnose and fix, so please don't use this to mess up your car. Each E46 sends different bus packets depending on the car's year and configuration. This likely won't be plug & play.

## Pre-Requisites
* python & python-setuptools 
	* `sudo apt-get install python python-setuptools`
* pyserial 
	* `pip install pyserial` 

## Optional Features
* **Bluetooth:** Send the car's steering wheel controls to a paired device. 
	* `sudo apt-get bluetooth bluez python-bluez` 
* **ZeroMQ:** Listen on a port for external commands. Opens up a janky REST api. 
	* https://github.com/MonsieurV/ZeroMQ-RPi 
* **MySQL:** Enables creating & logging most functions to a MySQL database. 
	* `sudo apt-get install mysql-server python-mysqldb` 

## Quick Start
* Install the prerequisites above 
* Plug in iBus USB device 
* Run: `./pyBus.py --device <PATH to USB Device>` 
	* E.g. `./pyBus.py --device /dev/ttyUSB0` 

## Advanced Usage
`./pyBus.py --device <PATH to USB Device> --with-bt <BT:MAC:ADDRESS> --with-zmq <ZMQ Port> --with-session <PATH to session file> --with-mysql <Username> <Password> <Database>` 

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