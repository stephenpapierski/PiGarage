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
#  

import RPi.GPIO as GPIO
import requests
import time
import json
from flask import Flask, request
from multiprocessing import Process, Value

class garageDoor():
    def __init__(self,closePin=29,openPin=31,relayPin=33,greenPin=11,yellowPin=13,redPin=15):
        #Setup pins
        GPIO.setup(closePin, GPIO.IN)
        GPIO.setup(openPin, GPIO.IN)
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
        self._isFullyClosed = None
        self._isFullyOpen = None
        self._wasFullyClosed = None
        self._wasFullyOpen = None
        self._status = None
        self._stopNew = False
        self._startTime = None
        self._statusFile = "piGarageStatus"
        self._settingsFile = "piGarageSettings"
        self._refresh = True
        # Run Configure with default params
        self.setControls(transitionTime=15, actuateDuration=1000, refresh=True)
        self._updateGPIOStatus()

    ##########################################################################
    # Public functions
    ##########################################################################

    def needsRefresh(self):
        return self._refresh

    # Update the configurable parameters of the sysem
    def setControls(self, transitionTime=None, actuateDuration=None, refresh=None):
        if (transitionTime):
            self._transitionTime = transitionTime
        if (actuateDuration):
            self._actuateDuration = actuateDuration
        if (refresh is not None):
            self._refresh = refresh

        self._writeSettings()

    def getControls(self):
        self._readSettings()

    # Try to close the garage door
    def closeDoor(self):
        self._readStatus()
        print('Status: '+self._status)

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
            print ("Valid status not found")

    # Try to open the garage door
    def openDoor(self):
        self._readStatus()
        print('Status: '+self._status)

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
            print ("Valid status not found")

    # This should be called frequenty in a main loop to keep everything up to date
    # @returns  (newStatus, status)
    #           newStatus   boolean     is this status new?
    #           status      string      current status value
    def checkNewStatus(self):
        isFullyClosed = self._isClosed()
        isFullyOpen = self._isOpen()
        newStatus = None

        # Check if the time has elapsed (door is stopped partially open)
        if (self._startTime):
            elapsedTime = time.time()-self._startTime
            if (elapsedTime > self._transitionTime):
                self._startTime = None
                newStatus = "stopped"

        # Check for new absolute states
        if (isFullyClosed != self._wasFullyClosed):
            # Report door is now fully closed
            if (isFullyClosed):
                newStatus = "closed"
                # Reset timer when we reach fully closed
                self._startTime = None
            # Report door is no longer closed
            else:
                newStatus = "opening"
                # Start timer
                self._startTime = time.time()
        elif (isFullyOpen != self._wasFullyOpen):
            # Report door is now fully open
            if(isFullyOpen):
                newStatus = "open"
                # Reset timer when we reach fully open
                self._startTime = None
            # Report door is no longer fully open
            else:
                newStatus = "closing"
                # Start timer
                self._startTime = time.time()
        if (isFullyOpen and isFullyClosed):
            newStatus = "unknown"

        self._wasFullyClosed = isFullyClosed
        self._wasFullyOpen = isFullyOpen

        if (newStatus):
            self._status = newStatus
            self._updateStatusLeds(newStatus)
            self._writeStatus()
            return (True, newStatus)
        else:
            # Report existing status
            return (False, self._status)

    ##########################################################################
    # Internal functions
    ##########################################################################

    # Check sensors and update global variables
    def _updateGPIOStatus(self):
        self._closed = GPIO.input(self._closePin)
        self._open = GPIO.input(self._openPin)

    # Return true if door is in FULLY closed position, false if not
    def _isClosed(self):
        self._updateGPIOStatus()
        return self._closed

    # Return true if door is in FULLY open position, false if not
    def _isOpen(self):
        self._updateGPIOStatus()
        return self._open

    # Actuate the relay to open/close door
    def _actuateRelay(self):
        print("Actuating Relay...")
        GPIO.output(self._relayPin, GPIO.HIGH)
        time.sleep(float(self._actuateDuration)/1000)
        GPIO.output(self._relayPin, GPIO.LOW)

    # Double actuate the relay to open/close door
    def _doubleActuateDoor(self):
        self._actuateRelay()
        time.sleep(self._actuateDuration/1000)
        self._actuateRelay()

    # Write the status to the statusFile. This should be performed by the main 
    # thread so that the background Flask thread can read the current status 
    # from the file.
    def _writeStatus(self):
        f = open(self._statusFile, "w")
        f.write(self._status)
        pass
    # Read the status from the statusFile. This should be performed by the 
    # background Flask thread to get the current status of the main thread.
    def _readStatus(self):
        f = open(self._statusFile, "r")
        self._status = f.read()

    # Write hubitat settings to the settings file. This should be performed by
    # the background Flask thread.
    def _writeSettings(self):
        settings = {}
        settings['transitionTime'] = self._transitionTime
        settings['actuateDuration'] = self._actuateDuration
        settings['refresh'] = self._refresh
        with open(self._settingsFile, "w") as outfile:
            json.dump(settings, outfile)

    # Read hubitat settings from the settings file. This shold be performed by 
    # the maain thread.
    def _readSettings(self):
        with open(self._settingsFile, "r") as json_file:
            data = json.load(json_file)
            self._transitionTime = data['transitionTime']
            self._actuateDuration = data['actuateDuration']
            self._refresh = data['refresh']

    def _updateStatusLeds(self, status):
        # Reset all status leds
        leds = (self._greenPin, self._yellowPin, self._redPin)
        GPIO.output(leds, GPIO.LOW)

        # if open -> red led
        if (self._status == "open"):
            setLeds = (self._redPin)
        # if closed -> green led
        elif (self._status == "closed"):
            setLeds = (self._greenPin)
        # if opening or closing -> yellow led
        elif (self._status == "opening" or self._status == "closing"):
            setLeds = (self._yellowPin)
        # if stopped -> yellow and red
        elif (self._status == "stopped"):
            setLeds = (self._yellowPin, self._redPin)
        else:
            setLeds = None
            print ("Valid status not found")

        if (setLeds):
            GPIO.output(setLeds, GPIO.HIGH)

# Main Program
# Flask app for receiving POST Requests
app = Flask(__name__)
@app.route('/PiGarage/open/', methods=['POST'])
def open_command():
    #print(request.form)
    garage.openDoor()
    return {'status':'Opening Garage Door...'}

@app.route('/PiGarage/close/', methods=['POST'])
def close_command():
    #print(request.form)
    garage.closeDoor()
    return {'status':'Closing Garage Door...'}

@app.route('/PiGarage/configure/', methods=['POST'])
def configure_command():
    data = request.get_json()
    transitionTime = data['transitionTime']
    actuateDuration = data['actuateDuration']
    garage.setControls(transitionTime=transitionTime, actuateDuration=actuateDuration, refresh=True)
    return {'status':'Configuring...'}

@app.route('/PiGarage/refresh/', methods=['POST'])
def refresh_command():
    time.sleep(1)
    garage.setControls(refresh = True)
    return {'status':'Refreshing...'}

# Main loop to run in the background
def garage_loop():
    while (True):
        garage.getControls()

        (newStatus, status) = garage.checkNewStatus()

        # Hubitat receives unsolicited http post requests on port 39501
        # and routes the message to the parse() method of the device 
        # with the matching DeviceNetworkId (IP, Mac, etc)
        if (newStatus or garage.needsRefresh()):

            if (newStatus):
                print("Posting new status")
            else:
                print("Posting refresh")
                garage.setControls(refresh = False)

            url = 'http://10.0.0.10:39501'
            body = {'status':status,'isNew':newStatus}
            r = requests.post(url, json=body)

            print("NewStatus: "+str(status))
        time.sleep(.1)

if __name__ == '__main__':
    GPIO.setmode(GPIO.BOARD)
    garage = garageDoor(closePin =  29, 
                        openPin  =  31, 
                        relayPin =  33)
    p = Process(target=garage_loop)
    p.start()
    app.run(host='0.0.0.0')
    p.join()

print("Cleaning up GPIO")
GPIO.cleanup()
