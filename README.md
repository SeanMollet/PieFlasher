# PieFlasher
Flash NOR and NAND flash chips quickly from a Raspberry PI. Supports 2,3,4,0,0W,0-2
Also supports integration with automated chip flashers.

## Initial setup

### The very beginning
Download the latest version of raspbian-lite and flash to an SD card.

From a freshly installed raspbian-lite

### Configure interfaces
sudo raspi-config
Go to Interfaces and enable I2C and SPI
Use your favorite text editor to edit /boot/config.txt and add the following line at the end (in the [all] section)

```
dtparam=i2c_arm=on,i2c_arm_baudrate=400000
```

### Install necessary tools
PieFlasher pre-requisites
```
sudo apt install git python3-pip i2c-tools 
```

Luma pre-requisites
```
sudo apt install python3-dev libfreetype6-dev libjpeg-dev build-essential
sudo apt install libsdl-dev libportmidi-dev libsdl-ttf2.0-dev libsdl-mixer1.2-dev libsdl-image1.2-dev
```

### Check the adapter
Run i2cdetect -y 1

If all is working correctly, you'll see:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 2f
30: -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- 4d -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

### Download and build flashrom

```
git clone https://github.com/flashrom/flashrom
cd flashrom
git checkout v.1.3.0

make -j 4
sudo make install
```
