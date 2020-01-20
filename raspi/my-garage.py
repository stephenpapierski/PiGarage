#!/usr/bin/env python3
import gpiozero
from flask import Flask, request

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
app = Flask(__name__)
@app.route('/myGarage/open/', methods=['POST'])
def open():
    print(request.form)
    return 'Opening Garage Door...'

@app.route('/myGarage/close/', methods=['POST'])
def close():
    print(request.form)
    return 'Closing Garage Door...'

if __name__ == '__main__':
    app.run(host='0.0.0.0')
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

