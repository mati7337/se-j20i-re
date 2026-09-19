# se-j20i-re

My journey to reversing the Sony Ericsson J20i dumbphone service protocol.

## Emulator

Used to reverse the protocol from different tools available online.

This has some advantages compared to just plugging a phone and observing wireshark:

- The mystery commands from proprietary tools get sent to an emulator instead of an
actual phone, so I have full control over what is done on the real device
- I can change phone parameters to experiment what changes in the tools
- The interface is more readable and I can do stuff like easily dump the loaders that
get sent to the device instead of copying them from the wireshark window

### Usage

```bash
# Run an USBIP server on 127.0.0.1:3240
python3 emulate.py

# Load the USBIP client driver
modprobe vhci_hcd

# Attach the USB device from the python server
usbip attach -r 127.0.0.1 -b 1-1
# or alternatively try to do it in a loop (to speed up the process)
./auto_attach.sh

# You can then attach the emulated USB device to e.g. a virtual machine
```

### How it works

To emulate a USB device it sets up an USBIP server implemented in python. I use modified
code from the following repo:

https://github.com/shadowbq/usbip-python3

which in turn seems to be a python3 port of

https://github.com/smulikHakipod/USB-Emulation

- `emulate.py` emulates the actual USB device using `USBIP.py` for USB/IP implementation and
`SonyEricsson.py` for emulating the actual device commands.
- `USBIP.py` is the USBIP implementation, it creates a server and implements a base USBDevice
class.
- `SonyEricsson.py` handles the actual commands, responds with values from device configs
from `SonyEricssonConfig.py`
- `EMPProto.py` protocol details, like the structure of different messages and some constants
- `SonyEricssonConfig.py` stores device specific info, like erom variables, device model etc.
- `common.py` common stuff like the BaseStructure class
- `auto_attach.py` tries to attach the USBIP device in a loop, speeds up restarting

## Client

Client for talking to a phone using the EMP protocol.

### Usage

```
usage: client.py [-h] [--emu] {test,enum-erom,read-erom} ...

positional arguments:
  {test,enum-erom,read-erom}
    test                Run the test function
    enum-erom           Find all non empty erom variables
    read-erom           Read an EROM variable

options:
  -h, --help            show this help message and exit
  --emu                 Only find emulated devices
```

The `--emu` parameter assumes that the USBIP device is under bus 7.
Without this parameter the client finds only real devices. Should probably change this.

### How it works

It uses the pyusb library for talking with the phone and structures from `EMPProto.py`.

- `client.py` handles connecting to the device using pyusb and implements functions
which pack supplied arguments into a proper structure from `EMPProto.py` and return
response as a structure from `EMPProto`.
- `EMPProto.py` protocol details, like the structure of different messages and some constants
- `common.py` common stuff like the BaseStructure class

## Other stuff

- `babe.py` WIP implementation of the babe format parser
- `certs.py` certificates from seftool's `certz.h`
- `qdecoder.py` decodes multiple Q messages from a single file

# Info about the phones

Structure of the EMP protocol messages is documented in `EMPProto.py`.

To enter the serivce mode first power off the device, hold either the C button or 2+5 then
connect the phone to your computer using a USB cable (e.g DCU-60 or DCU-65).

The device should be detected as
`0fce:adde Sony Ericsson Mobile Communications AB C2005 (Xperia M dual) in service mode`
even if it's not actually a C2005 Xperia M dual, they just use the same vid:pid

## Communication

When the service mode starts, the first thing sent by it is the hello message, in case
of DB3350 it's a single lowercase "z".

SEMC Service mode seems to be code running from the bootrom, couldn't find any dumps of it.

Phone then listens for regular commands which allow for example reading the chip id, CID,
Certificate color, IMEI, etc.

Command `Q` switches to a mode that seems to allow running of signed code. This is used
by different tools to run "loaders", which seem to be small pieces of code that expand
the capabilites of the service mode. They are sent in 3 parts:

- Header - BABE header, contain a x509 certificate
- Payload - The actual little-endian ARM v5t code
- Prologue - ???

Headers seem to use RSA with SHA1 x509 certificates, which are probably insecure.

## Certificate colors

SE phones can have different certificates:

- Blue - factory, never programmed
- Brown - developer phones, for testing/debugging/beta
- Red - retail phones

It seems to be possible to convert a red phone to a brown phone, which is used for unlocking.

There also seem to exist black certificates, but i couldn't find any useful info on them.

## CID

SE's protection present in the phone. New CIDs are deployed from time to time to prevent them from being unlocked/flashed/tampered with by non-SE service tools. The OTP and EROM of a phone might be protected by different CIDs.

## EMMA

Service software/solution by SE themselves. Protected by the EMMA smartcard to prevent non-licensed usage. Current version is EMMA3, though EMMA2 is still alive (but kinda useless on newer phones). The EMMA smartcard contains an algorithm that allows EMMA to communicate directly to/with the phones CID, so performing operations the way they were intended. The smartcard and its algorithm has not been cracked. Current EMMA access levels exists:Service Update - Can't unlock phones.Service Update Pro - Can't unlock phones.Network Operator - Can't unlock phones (but sure as hell can lock them ).Service Center Std - Can't unlock phones.Service Center Rc - Can unlock phones, as they have a special version of the smartcard with a CSCA key.Research & Development - Can unlock phones, as they have a special version of the smartcard with a CSCA key.

## GDFS

Phone's stash where settings and calibration data is stored (also firmwares IMEI-resource as well as SIMlocks). SImilar to NVRAM.

## Other random info

Unlocking DB2020 seems to require cracking something

https://web.archive.org/web/20070430165012/http://www.davinciteam.com/db2020.php

I'm guessing the rsa signature? They require the user to send a DVL file generated using "Save log" in dtvclient1774.zip, it's the "unlock client"

Info about CID, CDA, Certificate colors, GDFS, IMEI, EMMA and chipset IDs
https://technosmartphoneskhmer.blogspot.com/2015/06/sony-ericsson-general-informations.html

Some basic info about SE phones and tools
https://lpcwiki.miraheze.org

A command-line utility for flashing, unlocking, and managing Sony Ericsson AVR & ARM phones (DB1000, DB2000, DB2010, DB2012, DB2020, PNX5230) over a serial connection
Has some info about the EMP protocol and the BABE format. Packages loaders in binary form.
https://github.com/farid1991/seftool

Similar to seftool but in python, also serial only
https://gitea.osmocom.org/fixeria/sepytool/src/branch/main

There is some official info in the linux kernel from stericsson devs, especially in
linux-2.6.39/arch/arm/mach-u300/

Maybe useful?
https://github.com/siemens-mobile-dev/svn_boba_mirror/tree/master/SE/Library

## Proprietary tools

a2uploader

sefp2 plugin for Far

### to analyse later

aerix

babe2raw

elf2vkpex
