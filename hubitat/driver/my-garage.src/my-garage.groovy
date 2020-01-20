/**
 *  MyGarage Smart Garage Door Controller
 *
 *  Copyright 2020 Stephen Papierski
 *
 *  Licensed under the GNU General Public License v3.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the License at:
 *
 *      http://gnu.org/licenses/gpl-3.0.en.html
 *
 *  Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 *  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
 *  for the specific language governing permissions and limitations under the License.
 *
 *  Change History:
 *
 *    Date        Who                   What
 *    ----        ---                   ----
 *    2020-01-19  Stephen Papierski     Initial Commit
 * 
 */
metadata {
    definition (name: "MyGarage Door Controller", namespace: "PinionValleyProjects", author: "Stephen Papierski", importUrl: "https://github.com/stephenpapierski/myGarage/blob/master/hubitat/driver/my-garage.src/my-garage.groovy") {
        capability "GarageDoorControl"
        //capability "Lock"     //Enable ability to keep the garage door shut
        //capability "Chime"    //Enable ability to sound chime before closing door

        //attribute "percentOpen", "float"
        //attribute "partiallyOpen", "Boolean"

        command "open"
        command "close"
    }

    preferences {
        input(name: "deviceIP", type: "string", title:"Device IP Address", description: "Enter IP Address of your HTTP server", required: true, displayDuringSetup: true)
        input(name: "devicePort", type: "string", title:"Device Port", description: "Enter Port of your HTTP server (defaults to 80)", defaultValue: "80", required: false, displayDuringSetup: true)
        input(name: "devicePath", type: "string", title:"URL Path", description: "Rest of the URL.", displayDuringSetup: true)
    }
}

def parse(String description) {
    log.debug(description)
}

def close() {
    success = sendCmd(devicePath + "/close/")
    //if (success) {
        sendEvent(name: "garageDoorControl", value: "closing", isStateChanged: true)
    //}
}

def open() {
    success = sendCmd(devicePath + "/open/")
    //if (success) {
        sendEvent(name: "garageDoorControl", value: "opening", isStateChanged: true)
    //}
}

def sendCmd(String action) {
    def localDevicePort = (devicePort==null) ? "80" : devicePort 
    
    //TODO: Add variable sanitation (stripping / from front/back)
    //def params = [uri: "http://${username}:${password}@${ip}/${action}"]
    def params = [uri: "http://${deviceIP}:${localDevicePort}/${action}"]
    try { 
        httpPost(params) { resp -> 
            //log.debug(resp.isSuccess())
            //return resp.isSuccess()
        }
    }
    catch (Exception e) {
        log.debug "sendCmd hit exception ${e} on POST"
    }
}
