from i2c import i2c_adc, i2c_pot
from gpio import pi_gpio
from time import sleep

gpio = pi_gpio()
adc = i2c_adc()
pot = i2c_pot()

def getPotForVoltage(target):
    return 124-round((((5000/3)*(5*target-6))/50000)*127)


print("Setting voltage to 3.3")

print("pot:",getPotForVoltage(3.3))

pot.setPot(80)
gpio.setPsEn(True)
input()
gpio.setPwrEn(False)
sleep(.1)

input()

print("Current voltage:",round(adc.getVoltage(),2))    

