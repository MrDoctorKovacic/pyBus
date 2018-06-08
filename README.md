pyBus
=====
### Forked from ezeakeal's excellent [pyBus](https://github.com/ezeakeal/pyBus)

iBus interface for my E46 BMW written in Python. I'm using it for a backend to a Nexus 7 install, if you want more of a factory integration I recommend one of the other forks. 
This is to be used with the USB interface which can be acquired from [Reslers.de](http://www.reslers.de/IBUS/). Other USB interfaces should work just as well, although are untested. 

## Overview
* Interfaces with the BMW iBus to send and receive button presses, status changes, vehicle info, etc. 
* Listens on socket for predefined ibus functions to be run. 
* Handles Bluetooth media commands through dbus. Does NOT provide connection / pairing functionality. 

### Useful links
http://web.archive.org/web/20041204074622/www.openbmw.org/bus/  
http://web.comhem.se/bengt-olof.swing/ibusdevicesandoperations.htm   
http://www.online-rubin.de/BMW/I-Bus/I-BUS%20Codes%20e46.htm 

### Warning
All software is in early alpha stages! K/I-Bus issues can be painful to diagnose and fix, so please don't use this to mess up your car.

## Pre-Requisites
* ZeroMQ, used for communicating with the outside world. 
	* https://github.com/MonsieurV/ZeroMQ-RPi 
* python, python-setuptools, python-dev, bluetooth, bluez, python-bluez 
	* `apt-get install python python-setuptools bluetooth bluez python-bluez`
* **Python modules:** pyserial pyzmq
	* `pip install pyserial pyzmq` 
## How to use
* Install the prerequisites above 
* Plug in iBus USB device 
* Run: `./pyBus.py <PATH to USB Device>` 
	* E.g. `./pyBus.py /dev/ttyUSB0` 