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

import gpiozero
import requests
import time
from flask import Flask, request, jsonify
from multiprocessing import Process, Value

class distanceSensor(gpiozero.MCP3001):
    def __init__(self, max_voltage=3.3, **spi_args):
        super(distanceSensor, self).__init__(max_voltage, **spi_args)

    @property
    def distanceCM(self):
        return self.raw_value
    @property
    def closed(self):
        return self.value >= 1000
    @property
    def open(self):
        return self.value <= 100

# Main Program
# Flask app for receiving POST Requests
app = Flask(__name__)
@app.route('/PiGarage/open/', methods=['POST'])
def open():
    print(request.form)
    return 'Opening Garage Door...'

@app.route('/PiGarage/close/', methods=['POST'])
def close():
    print(request.form)
    return 'Closing Garage Door...'

def garage_loop():
    while (True):
        print("loop running")
        time.sleep (1)

if __name__ == '__main__':
    p = Process(target=garage_loop)
    p.start()
    app.run(host='0.0.0.0')
    p.join()

    while (True):
        print ("working")
#distanceS = distanceSensor(max_voltage = 3.3,
#                             clock_pin = 11,
#                             mosi_pin = 10,
#                             miso_pin = 9,
#                             select_pin = 7)
#
#
#while (True):
    #pass
#    print("raw: \t" + str(distanceS.raw_value))
#    print("CM: \t" + str(distanceS.distanceCM))
#    print("Closed: \t" + str(distanceS.closed))
#    print("Open: \t" + str(distanceS.open))

