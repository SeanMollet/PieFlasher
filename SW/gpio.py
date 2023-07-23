import RPi.GPIO as GPIO

class pi_gpio:
    def __init__(self) -> None:
        GPIO.setmode(GPIO.BCM)
        # ("Pin name", GPIO #, Initial value)
        self.pins = {}
        self.pins["SIG_NG"]=(22,True,GPIO.OUT)
        self.pins["SIG_OK"]=(23,True,GPIO.OUT)
        self.pins["SIG_BUSY"]=(24,True,GPIO.OUT)
        self.pins["SIG_START"]=(21,True,GPIO.IN)
        self.pins["PS_EN"]=(19,False,GPIO.OUT)
        self.pins["PWR_EN"]=(20,False,GPIO.OUT)

        for name in self.pins:
            pin = self.pins[name]
            print("Setting up",name,"GPIO:",pin[0],"default:",pin[1])
            if pin[2] == GPIO.OUT:
                GPIO.setup(pin[0],GPIO.OUT)
                GPIO.output(pin[0],pin[1])
            else:
                GPIO.setup(pin[0],GPIO.IN, pull_up_down=GPIO.PUD_UP)


    def __del__(self) -> None:
        GPIO.cleanup()

    def setPin(self, pin: str,value: bool):
        if self.pins[pin] is not None and self.pins[pin][2]==GPIO.OUT:
            GPIO.output(self.pins[pin][0],value)

    def getPin(self, pin: str) -> bool:
        if self.pins[pin] is not None and self.pins[pin][2]==GPIO.IN:
            return GPIO.input(self.pins[pin][0])

    def defaultPin(self,pin: str):
        if self.pins[pin] is not None:
            GPIO.output(self.pins[pin][0],self.pins[pin][1])
    def pinIsOutput(self, pin: str) -> bool:
        if self.pins[pin] is not None:
            return self.pins[pin][2] == GPIO.OUT
        return False


if __name__ == "__main__":
    print("Initializing GPIO")
    gpio = pi_gpio()

    print("IO pin testing")
    pins = ["SIG_NG","SIG_OK","SIG_BUSY","SIG_START"]
    for pin in pins:
        if gpio.pinIsOutput(pin):
            print("Setting",pin,"high, press enter to lower")
            gpio.setPin(pin,True)
            input()
            print("Press enter to set",pin,"low")
            input()
            gpio.setPin(pin,False)
            print("Press enter to continue")
            input()
            gpio.defaultPin(pin)
        else:
            value = gpio.getPin(pin)
            print("Value of",pin,"is:",value,"Press enter to check again")
            input()
            value = gpio.getPin(pin)
            print("Value of",pin,"is:",value,"Press enter to continue")




   