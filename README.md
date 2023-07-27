# PieFlasher
Flash NOR and NAND flash chips quickly from a Raspberry PI. Supports 2,3,4,0,0W,0-2
Also supports integration with automated chip flashers.

This software is not secure. The architecture is not secure. The code has some basic sanity checks, but there are countless ways it could be exploited. Don't expose it to the internet. You have been warned.

## Initial setup

### The very beginning
Download the latest version of raspbian-lite and flash to an SD card.

From a freshly installed raspbian-lite

### Configure hostname interfaces
sudo raspi-config
Go to system and then hostname and change the hostname. This name will show up in the flash interface, so make it unique for each device.
Then to go interface options and enable I2C and SPI
Use your favorite text editor to edit /boot/config.txt and edit the i2c_arm line, added the i2c_arm_baudrate part.

```
dtparam=i2c_arm=on,i2c_arm_baudrate=400000

```

Reboot the pi 

```
sudo reboot
```

### Install necessary tools
PieFlasher pre-requisites
```
sudo apt install git python3-pip i2c-tools python3-sphinx
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

By default, flashrom overwrites log files. This isn't a desirable behavior for us, so I've made a change to my version. I'll PR it upstream, but for now, use mine.

```
git clone https://github.com/SeanMollet/flashrom
cd flashrom

make -j 4
sudo make install
```

### The files

Most files in here can be run on their own and will do something useful.


| File | Solo usage |
| gpio.py | Test GPIO inputs/outputs |
| i2c.py | Test I2C ADC and digital POT |
| manualFlash.py | Flash a chip with a given file and voltage |
| power.py | Test the adjustable power supply (DO NOT HAVE A CHIP ATTACHED!)|
| worker_client.py | Connect to server and print messages |

### Running the system

#### Server

Install the pre-requisite python packages as per above on the client devices and on a server. 

The server is run with 

```
python3 server.py
```

It will open port 5000 on all interface. Open this in a browser to see the web interface. It stores log files and image files in data/logs and data/images respectively

#### Client

The client is run with:

```
python3 worker.py
```

The first time it's run it will save a configuration file in data/config. This file specifies the url of the server. Adjust as needed. 

To run the client automatically at startup, copy pieflasher.service to /etc/systemd/system. Edit the file, changing sean and /home/sean to your respective user and path where the repo is stored. Then run:

```
systemd enable pieflasher
```

This will automatically launch PieFlasher at startup and will restart it if it were to fail.
