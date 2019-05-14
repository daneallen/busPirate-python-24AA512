# busPirate-python-24AA512
A collection of python functions that interacts with the Bus Pirate in bitbang mode to read and write data to a 24AA512 EEPROM via I2C.

It's a work in progress, but the basics are as follows:

Runs with python 2.7

## optional arguments:
  -h, --help            show this help message and exit
  --port PORT, -p PORT  Serial port device
  --baud BAUD, -b BAUD  Serial port baud rate
  --start START, -s START
                        2 byte Start address to begin reading/writing from -
                        in hex (i.e. 0000 or f8d0)
  --chunk CHUNK, -c CHUNK
                        How many chunk bytes to either read or write
  --file FILE, -f FILE  The file to be used for writing to EEPROM or to be
                        saved as output when reading from EEPROM: if omitted
                        for reading then to stdout
  --read, -r            Read from the EEPROM
  --write, -w           Write to the memory spaces
  --overwrite OVERWRITE, -o OVERWRITE
                        Overwrite the EEPROM with a byte

There's certainly more improvement that can be made, but from my initial standpoint it's significantly cheaper to purchase a Bus Pirate than it is for a Microchip mplab pm3.

Bus Pirate, ~$30: https://www.sparkfun.com/products/12942
Microchip MPLAB PM3, ~$900: https://www.microchip.com/Developmenttools/ProductDetails/DV007004

## Future to dos:
1. Optimize the write delays so that it doesn't take as long and is still reliable
2. Upon a write, read back the original data and compare byte for byte before printing any success.
3. Make fully compatible with python3
