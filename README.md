pyBus
=====
## Forked from ezeakeal's excellent [pyBus](https://github.com/ezeakeal/pyBus)

iBus interface for my E46 BMW written in Python  
This is to be used with the USB interface which can be acquired from [Reslers.de](http://www.reslers.de/IBUS/)

## Overview
The main component:  
**pyBus.py** - interfaces with the iBus to send and receive button presses and vehicle status changes

### Useful links
http://web.archive.org/web/20041204074622/www.openbmw.org/bus/  
http://web.comhem.se/bengt-olof.swing/ibusdevicesandoperations.htm   

### Warning
All software is in early alpha stages! K/I-Bus issues can be painful to diagnose and fix, so please don't use this to mess up your car.

### Architecture/Operation
Soooon..

## Pre-Requisites
* python, python-setuptools, bluez, python-bluez
	* `apt-get install python python-setuptools bluez python-bluez
* **Python modules:** pyserial
	* `pip install pyserial`
## How to use
* Install the prerequisites above
* Plug in iBus USB device
* Run: `./pyBus.py <PATH to USB Device>`
	* E.g. `./pyBus.py /dev/ttyUSB0`

