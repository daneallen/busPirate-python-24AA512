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

def readEEPROM(port, startHighAddress=0, startLowAddress=0, limit=0xffff):

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
    port.read(1000)   #sloppy here, need to do better to keep track of ACK and other data on the port, easy enough to just read everything and start fresh

    for i in range(0,int(limit)-1):     #stop 1 byte short of the desired read amount to send:
        port.write('\x04')      # send read command
        port.write('\x06')      # send the ACK command

    port.write('\x04')          # send read command
    port.write('\x07')          # send the NACK command
    port.write('\x03')          # send the STOP command

    """
    Significantly faster to read ALL of the data and then post process it
    Tricky bit is removing all of the unwanted 0x01 ACKs
    """

    got = port.read(int(limit)*2)
    line = binascii.hexlify(got)
    #print(line)
    n=2
    line = [line[i:i+n] for i in range(0, len(line), n)]
    data = bytearray()
    for i in line[::n]:
        #data.append(i.decode("hex"))
        data.append(binascii.unhexlify(i))

    return data

def writeEntireEEPROM(port, char):
    temp = []
    for i in range(0,128):
        temp.append(int(char))

    highAddress = 0
    lowAddress = 0

    for i in range(0,512):
        pageWrite(port, bytearray(temp), highAddress, lowAddress)
        time.sleep(0.05)
        lowAddress+=128
        if(lowAddress == 256):
            lowAddress = 0
            highAddress+=1
        return True

def writeEEPROM(port, data, startHighAddress=0, startLowAddress=0):

    #can only write up to 128 bytes at a time per the datasheet... the first one and then 127 more which is called a Page write
    temp = []
    addressIndexOffset = 0

    for item in data:
        temp.append(item)
        addressIndexOffset+=1
        if(len(temp)==128):
            pageWrite(port, bytearray(temp), startHighAddress, startLowAddress) #need to convert the temp list to bytearray to keep similar
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
        pageWrite(port, bytearray(temp), startHighAddress, startLowAddress)

    #should really write a method to verify that the file was successfully written instead of this on faith response
    return True

def pageWrite(port, data, startHighAddress, startLowAddress):
    """
    Need to do more error checking to ensure that the address combination & data length
    don't result in a fouled data write (i.e. wrap within page boundary) as per the
    datasheet
    """

    if(len(data) > 129):
        print("Data to write exceeded 128 bytes, returning false")
        return False
    elif(len(data)+startLowAddress > 256):
        print("cannot pageWrite this combination as the data will wrap internally on the the page")
        return False

    else:
        port.write('\x02')                          #Start bit {
        port.write('\x10')                          #tell bus pirate we're going to write 1 byte
        port.write('\xa0')                          #write the control byte

        port.write('\x10')                          #tell bus pirate we're going to write 1 byte
        port.write(chr(startHighAddress))           #write the high address byte

        port.write('\x10')                          #tell bus pirate we're going to write 1 byte
        port.write(chr(startLowAddress))            #write the low address byte

        port.read(1000) #placeholder

        for x in range(0,len(data)):
            port.write('\x10')                      #tell bus pirate we're going to write 1 byte
            port.write(chr(data[x]))                #write the desired byte

            """
            #Per the datasheet, should simply wait for an ACK back to determine that the write was sucessful
            if(int(binascii.hexlify(port.read(2)),16)!= 0x0100):
                print("error in page write")    # when run this took significantly longer! Probably need to go back and read page by page for valid data.
            """

        port.write('\x03')                          #send the STOP bit
        time.sleep(.02)
        return True


def compareByteArray(inData, outData):
    if(len(inData) != len(outData)):
        print("compareByteArray failed the length check")
        return False

    for i in range(0,len(inData)):
        if( int(inData[i]) != (outData[i]) ):
            print("compareByteArray failed a single byte check at ["+str(i)+"]: " + str(int(inData[i]))+ " != " + str(int(outData[i])))
            return False;
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

        if(args.start != 0):
            startHighAddress = int(args.start[:2],16)
            startLowAddress = int(args.start[2:4],16)
        else:
            startHighAddress = 0
            startLowAddress = 0

        #configure the bus pirate with Power and pullups enabled
        port.write('\x4c')

        if(args.read):
            data = readEEPROM(port, startHighAddress, startLowAddress, int(args.chunk))
            if(args.file):
                outputFile = open(args.file, "wb")
                outputFile.write(data)
                print("Data file written!")
                outputFile.close()
            else:
                print(binascii.hexlify(data))

        elif(args.write):
            outputFile = open(args.file, "rb")
            data = bytearray(outputFile.read())
            outputFile.close()
            if(len(data) > 0xffff):
                print("Data file to write is too large for the EEPROM, exiting now.")
                return
            else:
                if(writeEEPROM(port, data, startHighAddress, startLowAddress)):
                    print("Sucessfully wrote " + args.file + " to the EEPROM")
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
