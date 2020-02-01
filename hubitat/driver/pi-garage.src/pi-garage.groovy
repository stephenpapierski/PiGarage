/**
 * PiGarage Smart Garage Door Controller
 *
 * Copyright 2020 Stephen Papierski
 *
 * Licensed under the GNU General Public License v3.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at:
 *
 *     http://gnu.org/licenses/gpl-3.0.en.html
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
 * for the specific language governing permissions and limitations under the License.
 *
 * Change History:
 *
 *   Date        Who                   What
 *   ----        ---                   ----
 *   2020-01-19  Stephen Papierski     Initial Commit
 * 
 */
metadata {
    definition (name: "PiGarage Door Controller", namespace: "PinionValleyProjects", author: "Stephen Papierski", importUrl: "https://raw.githubusercontent.com/stephenpapierski/PiGarage/master/hubitat/driver/pi-garage.src/pi-garage.groovy") {
        capability "GarageDoorControl"
        capability "Refresh"
        //capability "Lock"     //Enable ability to keep the garage door shut
        //capability "Chime"    //Enable ability to sound chime before closing door

        attribute "stoppedOpen", "Boolean"

        command "open"
        command "close"
    }

    preferences {
        input(name: "deviceIP", type: "string", title: "Device IP Address", description: "Enter IP Address of your HTTP server", required: true, displayDuringSetup: true)
        input(name: "devicePort", type: "string", title: "Device Port", description: "Enter Port of your HTTP server (defaults to 5000)", defaultValue: "5000", required: false, displayDuringSetup: true)
        input(name: "transitionTime", type: "number", title: "Transition Time", description: "Number of seconds it takes for door to transition from open to closed (round up).", defaultValue: "15", required: true, displayDuringSetup: true)
        input(name: "actuateDuration", type: "number", title: "Actuate Duration", description: "Number of milliseconds to actuate the relay to open or close the door.", defaultValue: "500", required: false, displayDuringSetup: true)
    }
}

//HTTP POST requests to port 39501 from a device that matches the Device Network Id end up here
def parse(String description) {
    def msg = parseLanMessage(description)
    def body=msg.body
    body = parseJson(body)
    def status = body.status
    def isNew = body.isNew
    //log.debug("Status = $status")
    if (status == "stopped"){
        sendEvent(name:"garageDoorControl", value:"open", isStateChanged:isNew)
        sendEvent(name:"stoppedOpen", value:true, isStateChanged:isNew)
    } else {
        sendEvent(name:"garageDoorControl", value:status, isStateChanged:isNew)
        sendEvent(name:"stoppedOpen", value:false, isStateChanged:isNew)
    }
    
}

def updated(){
    def postData = ["transitionTime":settings.transitionTime,"actuateDuration":settings.actuateDuration]
    sendCmd(devicePath + "/configure/", postData)
    refresh()
    
}

def close() {
    sendCmd(devicePath + "/close/", [:])
}

def open() {
    sendCmd(devicePath + "/open/", [:])
}

def refresh() {
    sendCmd(devicePath + "/refresh/", [:])
}

def sendCmd(String action, Map postData) {
    def localDevicePort = (devicePort==null) ? "5000" : devicePort 
    
    def url = "http://${deviceIP}:${localDevicePort}/${action}"
    
    try { 
        httpPostJson(url,postData) { resp -> 
            //log.debug(resp.isSuccess())
            //return resp.isSuccess()
        }
    }
    catch (Exception e) {
        log.debug "sendCmd hit exception ${e} on POST"
    }
}
