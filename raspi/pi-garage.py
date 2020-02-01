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
#   2020-01-19  Stephen Papierski     Initial Commit
#  

import RPi.GPIO as GPIO
import requests
import time
import json
from flask import Flask, request, jsonify
from multiprocessing import Process, Value

class garageDoor():
    def __init__(self, closePin = 29, openPin = 31, relayPin = 33):
        #Setup pins
        GPIO.setup(closePin,GPIO.IN)
        GPIO.setup(openPin,GPIO.IN)
        GPIO.setup(relayPin, GPIO.OUT)

        self._closePin = closePin
        self._openPin = openPin
        self._relayPin = relayPin
        self._isFullyClosed = None
        self._isFullyOpen = None
        self._wasFullyClosed = None
        self._wasFullyOpen = None
        self._status = None
        self._stopNew = False
        self._startTime = None
        self._statusFile = "piGarageStatus"
        # Run Configure with default params
        #TODO default to 15 seconds
        self.updateSettings(transitionTime=30, actuateDuration = 1000)
        self._updateGPIOStatus()

    ##########################################################################
    # Public functions
    ##########################################################################

    # Update the configurable parameters of the sysem
    def updateSettings(self, transitionTime, actuateDuration):
        #self._urlPath = urlPath
        self._transitionTime = transitionTime
        self._actuateDuration = actuateDuration

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
            print ("Didn't do anything")

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
            print ("Didn't do anything")

    # This should be called frequenty in a main loop to keep everything up to date
    # @returns  (newStatus, status)
    #           newStatus   boolean     is this status new?
    #           status      string      current status value
    def checkNewStatus(self):
        isFullyClosed = self._isFullyClosed()
        isFullyOpen = self._isFullyOpen()
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
    def _isFullyClosed(self):
        self._updateGPIOStatus()
        return self._closed

    # Return true if door is in FULLY open position, false if not
    def _isFullyOpen(self):
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


# Main Program
# Flask app for receiving POST Requests
app = Flask(__name__)
@app.route('/PiGarage/open/', methods=['POST'])
def open_command():
    #print(request.form)
    garage.openDoor()
    return 'Opening Garage Door...'

@app.route('/PiGarage/close/', methods=['POST'])
def close_command():
    #print(request.form)
    garage.closeDoor()
    return 'Closing Garage Door...'

# Main loop to run in the background
def garage_loop():
    while (True):
        (newStatus, status) = garage.checkNewStatus()

        # Hubitat receives unsolicited http post requests on port 39501
        # and routes the message to the parse() method of the device 
        # with the matching DeviceNetworkId (IP, Mac, etc)
        if (newStatus):
            print("Posting new status")

            url = 'http://10.0.0.10:39501'
            body = {'status':status}
            r = requests.post(url, json=body)

            print("NewStatus: "+str(status))

        time.sleep (1)

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
