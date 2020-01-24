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
        self._updateStatus()

    # Check sensors and update global variables
    def _updateStatus(self):
        self._closed = GPIO.input(self._closePin)
        self._open = GPIO.input(self._openPin)

    # Actuate the relay to open/close door
    def _actuateDoor(self):
        GPIO.output(self._relayPin, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(self._relayPin, GPIO.LOW)

    # Return true if door is in FULLY closed position, false if not
    def isFullyClosed(self):
        self._updateStatus()
        return self._closed

    # Return true if door is in FULLY open position, false if not
    def isFullyOpen(self):
        self._updateStatus()
        return self._open

    def closeDoor(self):
        if not self.isFullyClosed():
            self._actuateDoor()
            print("Close Door")
        else:
            print("Door already closed")

    def openDoor(self):
        if not self.isFullyOpen():
            self._actuateDoor()
            print("Open Door")
        else:
            print("Door already open")


    def getStatus(self):
        isFullyClosed = self.isFullyClosed()
        isFullyOpen = self.isFullyOpen()
        newStatus = None

        if (isFullyClosed != self._wasFullyClosed):
            # Report door is now fully closed
            if (isFullyClosed):
                newStatus = "closed"
            # Report door is no longer closed
            else:
                newStatus = "opening"
        elif (isFullyOpen != self._wasFullyOpen):
            # Report door is now fully open
            if(isFullyOpen):
                newStatus = "open"
            # Report door is no longer fully open
            else:
                newStatus = "closing"
        if (isFullyOpen and isFullyClosed):
            newStatus = "unknown"

        self._wasFullyClosed = isFullyClosed
        self._wasFullyOpen = isFullyOpen

        if (newStatus):
            self._status = newStatus
            return (True, newStatus)
        else:
            return (False, self._status)

# Main Program
# Flask app for receiving POST Requests
app = Flask(__name__)
@app.route('/PiGarage/open/', methods=['POST'])
def open():
    #print(request.form)
    garage.openDoor()
    return 'Opening Garage Door...'

@app.route('/PiGarage/close/', methods=['POST'])
def close():
    #print(request.form)
    garage.closeDoor()
    return 'Closing Garage Door...'

# Main loop to run in the background
def garage_loop():
    while (True):
        (newStatus, status) = garage.getStatus()

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
