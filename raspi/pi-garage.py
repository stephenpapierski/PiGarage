#!/usr/bin/env python3
#
# PiGarage Smart Garage Door Controller
#
# Copyright 2020 Stephen Papierski
#
# Licensed under the GNU General Public License v3.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at:
#
#     http://gnu.org/licenses/gpl-3.0.en.html
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations under the License.
#
# Change History:
#
#   Date        Who                   What
#   ----        ---                   ----
#   2020-01-19  Stephen Papierski     Initial release
#   2020-11-22  Stephen Papierski     Making simpler and more reliable with single thread and interrupts
#  

import RPi.GPIO as GPIO
import requests
import time
import json
import threading
from flask import Flask, request
from os import path

class garageDoor():
    def __init__(self,closePin=29,openPin=31,relayPin=33,greenPin=11,yellowPin=13,redPin=15):
        #Setup pins and interrupt call backs
        GPIO.setup(closePin, GPIO.IN)
        GPIO.add_event_detect(closePin, GPIO.BOTH, callback=self._checkDoorChanged)
        GPIO.setup(openPin, GPIO.IN)
        GPIO.add_event_detect(openPin, GPIO.BOTH, callback=self._checkDoorChanged)
        GPIO.setup(relayPin, GPIO.OUT)
        GPIO.setup(greenPin, GPIO.OUT)
        GPIO.setup(yellowPin, GPIO.OUT)
        GPIO.setup(redPin, GPIO.OUT)

        self._closePin = closePin
        self._openPin = openPin
        self._relayPin = relayPin
        self._greenPin = greenPin
        self._yellowPin = yellowPin
        self._redPin = redPin
        self._status = None
        self._settingsFile = "piGarageSettings"
        self._hubIp = None
        # Run Configure with default params
        # If settings fail to load from file, set defaults
        if (self._readSettings()):
            print("No existing settings, writing default")
            self.setControls(transitionTime=15, actuateDuration=1000)

        self._checkDoorChanged(None)


    ##########################################################################
    # Public functions
    ##########################################################################

    """
    Update the configurable parameters of the sysem
    """
    def setControls(self, transitionTime=None, actuateDuration=None, hubIp=None):
        if (transitionTime):
            self._transitionTime = transitionTime
        if (actuateDuration):
            self._actuateDuration = actuateDuration
        if (hubIp):
            self._hubIp = hubIp

        self._writeSettings()

    """
    Get IP of the hubitat hub
    """
    def hubIp(self):
        return self._hubIp

    """
    Try to close the garage door
    """
    def closeDoor(self):
        print('Requesting door close')

        # if open -> actuate 1x
        if (self._status == "open"):
            self._actuateRelay()
            print ("Door closing")
        # if closed -> do nothing
        elif (self._status == "closed"):
            print ("Door already closed")
        # if opening -> actuate 2x
        elif (self._status == "opening"):
            self._doubleActuateDoor()
            print ("Door stopping then closing")
        # if closing -> do nothing
        elif (self._status == "closing"):
            print ("Door already closing")
        # if stopped -> actuate 1x
        elif (self._status == "stopped"):
            self._actuateRelay()
            print("Door closing")
        else:
            print("Door in unknown state, actuating relay")
            self._actuateRelay()

    """
    Try to open the garage door
    """
    def openDoor(self):
        print('Requesting door open')

        # if open -> do nothing
        if (self._status == "open"):
            print ("Door already open")
        # if closed -> actuate 1x
        elif (self._status == "closed"):
            self._actuateRelay()
            print ("Door opening")
        # if opening -> do nothing
        elif (self._status == "opening"):
            print ("Door already opening")
        # if closing -> actuate 1x
        elif (self._status == "closing"):
            self._actuateRelay()
            print ("Door opening")
        # if stopped -> actuate 2x
        elif (self._status == "stopped"):
            self._doubleActuateDoor()
            print ("Door closing then opening")
        else:
            print ("Door in unknown state, actuating relay")
            self._actuateRelay()

    def refreshHubitat(self):
        if (self._hubIp):
            url = 'http://'+self._hubIp+':39501'
            body = {'status':self._status,'isNew':False}
            r = requests.post(url, json=body)
            print("Sending refresh status (" + self._status +") to hub (" + str(self._hubIp) + ")")


    ##########################################################################
    # Internal functions
    ##########################################################################

    """
    Actuate the relay to open/close door
    """
    def _actuateRelay(self):
        print("Actuating Relay...")
        GPIO.output(self._relayPin, GPIO.HIGH)
        time.sleep(float(self._actuateDuration)/1000)
        GPIO.output(self._relayPin, GPIO.LOW)

    """
    Double actuate the relay to open/close door
    """
    def _doubleActuateDoor(self):
        self._actuateRelay()
        time.sleep(self._actuateDuration/1000)
        self._actuateRelay()

    """
    Write hubitat settings to the settings file
    """
    def _writeSettings(self):
        print("Writing settings...")
        settings = {}
        settings['transitionTime'] = self._transitionTime
        settings['actuateDuration'] = self._actuateDuration
        settings['hubIp'] = self._hubIp
        with open(self._settingsFile, "w") as outfile:
            json.dump(settings, outfile)

        print("transitionTime = " + str(self._transitionTime) + "s")
        print("actuateDuration = " + str(self._actuateDuration) + "ms")
        print("hubIp = " + str(self._hubIp))

    """
    Read hubitat settings from the settings file
    """
    def _readSettings(self):
        if (path.exists("./" + self._settingsFile)):
            print("Reading in settings...")
            with open(self._settingsFile, "r") as json_file:
                data = json.load(json_file)
                self._transitionTime = data['transitionTime']
                self._actuateDuration = data['actuateDuration']
                self._hubIp = data['hubIp']

            print("transitionTime = " + str(self._transitionTime) + "s")
            print("actuateDuration = " + str(self._actuateDuration) + "ms")
            print("hubIp = " + str(self._hubIp))
            return 0
        else:
            return 1

    """
    Update the LED indicators based on the status
    """
    def _updateStatusLeds(self, status):
        # Reset all status leds
        leds = (self._greenPin, self._yellowPin, self._redPin)
        GPIO.output(leds, GPIO.LOW)

        # if open -> red led
        if (status == "open"):
            setLeds = (self._redPin)
        # if closed -> green led
        elif (status == "closed"):
            setLeds = (self._greenPin)
        # if opening or closing -> yellow led
        elif (status == "opening" or self._status == "closing"):
            setLeds = (self._yellowPin)
        # if stopped -> yellow and red
        elif (status == "stopped"):
            setLeds = (self._yellowPin, self._redPin)
        elif (status == "unknown"):
            setLeds = (self._greenPin, self._yellowPin, self._redPin)
        else:
            setLeds = None
            print ("Unknown LED state")

        if (setLeds):
            GPIO.output(setLeds, GPIO.HIGH)

    """
    Handler for when the door opens or closes. This should be called at startup and when
    the interrupt handler for the door stat sensors fire.
    """
    def _checkDoorChanged(self, pin):
        doorClosed = GPIO.input(self._closePin)
        doorOpen = GPIO.input(self._openPin)
        newStatus = None

        # Door is closed
        if (doorClosed and not doorOpen):
            if (self._status != "closed"):
                newStatus = "closed"
                print("Status: Door is closed")
        # Door is open
        elif (doorOpen and not doorClosed):
            if (self._status != "open"):
                newStatus = "open"
                print("Status: Door is open")
        # Somewhere in between
        elif (not doorOpen and not doorClosed):
            if (pin == self._closePin and self._status == "closed"):
                newStatus = "opening"
                print("Status: Door is opening")
                # Check if door stopped after transitionTime
                threading.Timer(self._transitionTime, self._doorStopped).start()
            elif (pin == self._openPin and self._status == "open"):
                newStatus = "closing"
                print("Status: Door is closing")
                # Check if door stopped after transitionTime
                threading.Timer(self._transitionTime, self._doorStopped).start()
            elif (pin == None):
                # this only happens during startup when pin = None (not an interrupt)
                newStatus = "open"
                print("Status: Pin is None, Door is unknown, assume open")
        elif (doorOpen and doorClosed):
            self._status = "unknown"
            print("Status: Door is unknown")
        else:
            self._status = "unknown"
            print("This shouldn't happen, setting door to unknown")


        if (newStatus):
            self._updateStatusAll(newStatus)

    """
    This should be called after a timer interupt. If the door hasn't finish opening or
    closing, it will assume the door has stopped open, and report open.
    """
    def _doorStopped(self):
        if (self._status != "open" and self._status != "closed"):
            print("Door stopped, reporting open")
            self._updateStatusAll("open")

    """
    Update the local status, Hubitat status, and LED status
    """
    def _updateStatusAll(self, newStatus):
        self._status = newStatus
        self._updateStatusLeds(newStatus)
        if (self._hubIp):
            url = 'http://'+self._hubIp+':39501'
            body = {'status':newStatus,'isNew':True}
            r = requests.post(url, json=body)
            print("Sending status (" + newStatus +") to hub (" + str(self._hubIp) + ")")

# Main Program
# Flask app for receiving POST Requests
app = Flask(__name__)
@app.route('/PiGarage/open/', methods=['POST'])
def open_command():
    garage.openDoor()
    # Update hub ip
    if (not garage.hubIp()):
        garage.setControls(hubIp=request.remote_addr)
    return {'status':'Opening Garage Door...'}

@app.route('/PiGarage/close/', methods=['POST'])
def close_command():
    garage.closeDoor()
    # Update hub ip
    if (not garage.hubIp()):
        garage.setControls(hubIp=request.remote_addr)
    return {'status':'Closing Garage Door...'}

@app.route('/PiGarage/configure/', methods=['POST'])
def configure_command():
    data = request.get_json()
    transitionTime = data['transitionTime']
    actuateDuration = data['actuateDuration']
    hubAddr = request.remote_addr
    garage.setControls(transitionTime=transitionTime, actuateDuration=actuateDuration, hubIp=hubAddr)
    return {'status':'Configuring...'}

@app.route('/PiGarage/refresh/', methods=['POST'])
def refresh():
    # Update hub ip
    if (not garage.hubIp()):
        garage.setControls(hubIp=request.remote_addr)
    garage.refreshHubitat()
    return {'status':'Refreshing Hubitat...'}

if __name__ == '__main__':
    GPIO.setmode(GPIO.BOARD)
    garage = garageDoor(closePin =  29, 
                        openPin  =  31, 
                        relayPin =  33)
    app.run(host='0.0.0.0')

print("Cleaning up GPIO")
GPIO.cleanup()
