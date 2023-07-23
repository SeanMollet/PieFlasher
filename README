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

### Install necessary tools
sudo apt install git python3-pip i2c-tools

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
git checkout v.1.3.0

make -j 4
sudo make install
```
