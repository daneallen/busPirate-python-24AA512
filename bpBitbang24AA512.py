#!/usr/bin/env python
# encoding: utf-8
"""
Example code to interface the Bus Pirate in binary mode
Brent Wilkins 2015
as found at Sparkfun.com
https://learn.sparkfun.com/tutorials/bus-pirate-v36a-hookup-guide

***** This script AS IS is tuned very specifically to the MicroChip 24AA512 EEPROM ****
It's imperative that the datasheet be understood for reading from random address spaces
and then mimicked in the Bus Pirate Binary mode of operation

Lot's of room to improve the reliability and feature set of this script.
1. Have not yet figured out how to reliably exit from the bitbang mode of operation
2. Time delays for writing are arbitraily picked, room to optomize them

This code requires pyserial:
    $ sudo pip install pyserial
or:
    $ sudo easy_install -U pyserial
"""
import sys
import serial
import argparse
import binascii
import time

commands = {
        'BBIO1': '\x00',    # Enter reset binary mode
        'SPI1':  '\x01',    # Enter binary SPI mode
        'I2C1':  '\x02',    # Enter binary I2C mode
        'ART1':  '\x03',    # Enter binary UART mode
        '1W01':  '\x04',    # Enter binary 1-Wire mode
        'RAW1':  '\x05',    # Enter binary raw-wire mode
        'RESET': '\x0F',    # Reset Bus Pirate
        'STEST': '\x10',    # Bus Pirate self-tests
}

def arg_auto_int(x):
    return int(x, 0)

class FatalError(RuntimeError):
    def __init__(self, message):
        RuntimeError.__init__(self, message)

def readEEPROM(port, args, startHighAddress=0, startLowAddress=0):

    #this is all very tuned specific to the 24AA512 EEPROM
    #trying to replicate the following interactive command I2C>{0xa0 0x00 0x00 { 0xa1 r:16
    port.write('\x02')  #Start command i.e. {
    port.write('\x10')  #write 1 byte
    port.write('\xa0')  #write the byte 0xa0 for adressing 24AA512 0

    #Start address
    port.write('\x10')                       #write 1 byte
    port.write(chr(startHighAddress))        #write the byte as read from args.start

    port.write('\x10')                       #write 1 byte
    port.write(chr(startLowAddress))         #write the byte as read from args.start

    port.write('\x02')  #Start command {
    port.write('\x10')  #write 1 byte
    port.write('\xa1')  #write the byte 0xa1

    #address setup is complete
    port.read(50)   #sloppy here, need to do better to keep track of ACK and other data on the port, easy enough to just read everything and start fresh

    print("Beginning the Read process")
    for i in range(0,int(args.chunk)):
        port.write('\x04')      # send read command
        port.write('\x06')      # send the ACK command

    """
    Significantly faster to read ALL of the data and then post process it
    Tricky bit is removing all of the unwanted 0x01 ACKs
    """

    got = port.read(int(args.chunk)*2)
    line = binascii.hexlify(got)
    n=2
    line = [line[i:i+n] for i in range(0, len(line), n)]
    data = bytearray()
    for i in line[::n]:
        data.append(i.decode("hex"))

    if(args.file):
        outputFile = open(args.file, "wb")
        outputFile.write(data)
        print("Data file written!")
        outputFile.close()
    else:
        print(binascii.hexlify(data))

def writeEntireEEPROM(port, char):
    temp = []
    for i in range(0,128):
        temp.append(int(char))

    #print(temp)
    highAddress = 0
    lowAddress = 0

    for i in range(0,512):
        pageWrite(port, temp, highAddress, lowAddress)
        time.sleep(0.05)
        lowAddress+=128
        if(lowAddress == 256):
            lowAddress = 0
            highAddress+=1
    print("All done, flashed the EEPROM with: " + binascii.hexlify(char))

def writeEEPROM(port, args, startHighAddress=0, startLowAddress=0):

    #can only write up to 128 bytes at a time per the datasheet... the first one and then 127 more which is called a Page write
    outputFile = open(args.file, "rb")
    data = bytearray(outputFile.read())
    outputFile.close()

    temp = []
    addressIndexOffset = 0

    for item in data:
        temp.append(item)
        addressIndexOffset+=1
        if(len(temp)==128):
            pageWrite(port, temp, startHighAddress, startLowAddress)
            time.sleep(0.05)
            startLowAddress+=128
            del temp[:]


        if(addressIndexOffset % 256 == 0):
            startLowAddress = 0
            addressIndexOffset = 0
            startHighAddress+=1

    #write the last part... may be incomplete i.e. less than a full 128 byte page
    print("There's a partial page section to still write")
    if(startLowAddress == 256):
        startLowAddress = 0
        startHighAddress+=1

    if(startHighAddress <= 255):    #not going to loop back around to the beginning of the memory
        pageWrite(port, temp, startHighAddress, startLowAddress)
        time.sleep(0.005)

    #should really write a method to verify that the file was successfully written instead of this on faith response
    print("Sucessfully wrote: " + args.file + " to the EEPROM")

def pageWrite(port, data, startHighAddress, startLowAddress):
    if(len(data) > 129):
        return False
    else:
        port.write('\x02')                          #Start bit {
        port.write('\x10')                          #tell bus pirate we're going to write 1 byte
        port.write('\xa0')                          #write the control byte

        port.write('\x10')                          #tell bus pirate we're going to write 1 byte
        port.write(chr(startHighAddress))           #write the high address byte

        port.write('\x10')                          #tell bus pirate we're going to write 1 byte
        port.write(chr(startLowAddress))            #write the low address byte

        for x in range(0,len(data)):
            port.write('\x10')                      #tell bus pirate we're going to write 1 byte
            port.write(chr(data[x]))                #write the desired byte
            time.sleep(.001)                        #this is a guess but seems to be enough time to write reliably

        port.write('\x03')                          #send the STOP bit
    return True


def main():
    parser = argparse.ArgumentParser(description = 'Bus Pirate binary interface for programming 24AA512 EEPROM via I2C', prog = 'binaryMode')

    parser.add_argument(
            '--port', '-p',
            help = 'Serial port device',
            default = '/dev/tty.usbserial-AC01PEA1')

    parser.add_argument(
            '--baud', '-b',
            help = 'Serial port baud rate',
            type = arg_auto_int,
            default = 115200)

    parser.add_argument(
            '--start', '-s',
            help = '2 byte Start address to begin reading/writing from - in hex (i.e. 0000 or f8d0)',
            default = 0x0000)

    parser.add_argument(
            '--chunk', '-c',
            help = 'How many chunk bytes to either read or write',
            default = 0xffff)

    parser.add_argument(
            '--file', '-f',
            help = 'The file to be used for writing to EEPROM or to be saved as output when reading from EEPROM: if ommitted for reading then to stdout')

    parser.add_argument(
            '--read', '-r',
            help = 'Read from the EEPROM',
            action = 'store_true')

    parser.add_argument(
            '--write', '-w',
            help = 'Write to the memory spaces',
            action = 'store_true')

    parser.add_argument(
            '--overwrite', '-o',
            help = 'Overwrite the EEPROM with a byte')

    args = parser.parse_args()

    print('\nTrying port: '+ str(args.port) + ' at baudrate: ' + str(args.baud))

    try:
        port = serial.Serial(args.port, args.baud, timeout=0.1)
    except Exception as e:
        print('I/O error({0}): {1}'.format(e.errno, e.strerror))
        print('Port cannot be opened')
    else:
        #print('Entering binary mode...\n')
        count = 0
        done = False
        while count < 20 and not done:
            count += 1
            port.write(commands.get('BBIO1'))
            got = port.read(5)  # Read up to 5 bytes
            if got == 'BBIO1':
                done = True
        if not done:
            port.close()
            raise FatalError('Buspirate failed to enter binary mode')

        # Now that the Buspirate is in binary mode, choose a BP mode
        port.write(commands.get('I2C1'))
        while True:
            got = port.readline()
            if not got:
                break
            #print(got),

        #print "Current I2C version: "
        #port.write('\x01')
        #got = port.readline()

        if(args.start != 0):
            startHighAddress = int(args.start[:2],16)
            startLowAddress = int(args.start[2:4],16)
        else:
            startHighAddress = 0
            startLowAddress = 0

        #configure the bus pirate with Power and pullups enabled
        port.write('\x4c')

        if(args.read):
            readEEPROM(port, args, startHighAddress, startLowAddress)
        elif(args.write):
            writeEEPROM(port, args, startHighAddress, startLowAddress)
        elif(args.overwrite):
            print(int(args.overwrite))
            writeEntireEEPROM(port, args.overwrite)


        print("All done: turning off the power and reseting the bus pirate")
        port.write('\x40')      #turn off the power and pullup resistors
        port.close()


if __name__ == '__main__':
    try:
        main()
    except FatalError as e:
        print('\nA fatal error occurred: %s' % e)
        sys.exit(2)
