# Emulates the sony ericsson in service mode to reverse engineer the protocol
# by using the old proprietary tools

import time
import random
import datetime
import errno
from USBIP import BaseStructure, USBDevice, InterfaceDescriptor, DeviceDescriptor, DeviceConfiguration, EndpointDescriptor, USBContainer, DeviceQualifierDescriptor, StandardDeviceRequest, USBIP_DIR_OUT, USBIP_DIR_IN
from SonyEricsson import SonyEricsson
import EMPProto

def encode_usb_string(string):
    if type(string) is bytes:
        # Raw bytes
        out = b"\x03" + string
    elif type(string) is str:
        # Unicode string
        out = b"\x03" + string.encode("utf-16le")
    else:
        raise ValueError("Expected either a string or bytes")

    return bytes([len(out) + 1]) + out

USB_CTRL_IN  = 0x80
USB_CTRL_OUT = 0x0

DESCRIPTOR_DEVICE                    = 1
DESCRIPTOR_CONFIGURATION             = 2
DESCRIPTOR_STRING                    = 3
DESCRIPTOR_INTERFACE                 = 4
DESCRIPTOR_ENDPOINT                  = 5
DESCRIPTOR_DEVICE_QUALIFIER          = 6
DESCRIPTOR_OTHER_SPEED_CONFIGURATION = 7
DESCRIPTOR_INTERFACE_POWER           = 8
DESCRIPTOR_DEBUG                     = 0xa

DESCRIPTOR_TYPES = {
    DESCRIPTOR_DEVICE: "DEVICE",
    DESCRIPTOR_CONFIGURATION: "CONFIGURATION",
    DESCRIPTOR_STRING: "STRING",
    DESCRIPTOR_INTERFACE: "INTERFACE",
    DESCRIPTOR_ENDPOINT: "ENDPOINT",
    DESCRIPTOR_DEVICE_QUALIFIER: "DEVICE_QUALIFIER",
    DESCRIPTOR_OTHER_SPEED_CONFIGURATION: "OTHER_SPEED_CONFIGURATION",
    DESCRIPTOR_INTERFACE_POWER: "INTERFACE_POWER",
    DESCRIPTOR_DEBUG: "DEBUG"
}

CTRL_GET_STATUS = 0x00
CTRL_GET_DESCRIPTOR = 0x06
CTRL_GET_CONFIGURATION = 0x08
CTRL_SET_CONFIGURATION = 0x09

class USBSE(USBDevice):
    # The Sony Ericsson device in a service mode
    # Emulates the USB stuff
    # The EMP message handling stuff is in SonyEricsson.py

    # The GET_DESCRIPTOR strings
    USB_STRING_LANG = 0
    USB_STRING_MANUFACTURER = 1
    USB_STRING_PRODUCT = 2
    USB_STRING_CONFIGURATION = 3
    USB_STRING_INTERFACE = 4

    usb_strings = {
        USB_STRING_LANG:          encode_usb_string(b"\x09\x04"),
        USB_STRING_MANUFACTURER:  encode_usb_string("Sony Ericsson"),
        USB_STRING_PRODUCT:       encode_usb_string("SEMCBOOT Download"),
        USB_STRING_CONFIGURATION: encode_usb_string("C1"),
        USB_STRING_INTERFACE:     encode_usb_string("I1"),
    }

    interface_d = InterfaceDescriptor(bAlternateSetting=0,
                                      bNumEndpoints=2,
                                      bInterfaceClass=0xff,
                                      bInterfaceSubClass=0,
                                      bInterfaceProtocol=0xff,
                                      iInterface=USB_STRING_INTERFACE)

    end_point_in = EndpointDescriptor(bEndpointAddress=EMPProto.USB_EP_IN,
                         bmAttributes=0x2,
                         wMaxPacketSize=0x0040,
                         bInterval=0x0)  # interval to report

    end_point_out = EndpointDescriptor(bEndpointAddress=EMPProto.USB_EP_OUT,
                         bmAttributes=0x2,
                         wMaxPacketSize=0x0040,
                         bInterval=0x0)  # interval to report

    device_descriptor = DeviceDescriptor(bcdUSB=0x0200,
                                            bDeviceClass=0xff,
                                            bDeviceSubClass=0x0,
                                            bDeviceProtocol=0xff,
                                            bMaxPacketSize0=64,
                                            idVendor=EMPProto.USB_VID,
                                            idProduct=EMPProto.USB_PID,
                                            bcdDevice=0x0100,
                                            iManufacturer=USB_STRING_MANUFACTURER,
                                            iProduct=USB_STRING_PRODUCT,
                                            bNumConfigurations=1)

    configuration = DeviceConfiguration(wTotalLength=0x0020,
                                        bNumInterfaces=0x1,
                                        bConfigurationValue=1,
                                        iConfiguration=USB_STRING_CONFIGURATION,
                                        bmAttributes=0xc0,
                                        bMaxPower=48)  # 96 mA current

    interface_d.endpoints = [end_point_in, end_point_out]
    interface = [interface_d] # List of interface alternatives
    configuration.interfaces = [interface]   # Supports only one interface
    configurations = [configuration]  # Supports only one configuration

    def __init__(self):
        USBDevice.__init__(self)
        self.sony_ericsson = SonyEricsson(self)

    def handle_usb_unlink(self, unlink_seqnum) -> int:
        # NOTE: idk if the status is right, but it seems to work
        print(f"Unlinking {unlink_seqnum}")

        for i, usb_req in enumerate(self.sony_ericsson.usb_req_queue):
            if usb_req.seqnum == unlink_seqnum:
                del self.sony_ericsson.usb_req_queue[i]
                return 0

        return 0

    def handle_data(self, usb_req):

        if usb_req.direction == USBIP_DIR_IN:
            # device -> host
            print("\n\033[32m====== Device -> Host ======\033[0m")
            #print("usb_req:", vars(usb_req))

            self.sony_ericsson.handle_in(usb_req)

        elif usb_req.direction == USBIP_DIR_OUT:
            # host -> device
            print("\n\033[34m====== Host -> Device ======\033[0m")
            print("Raw:", usb_req.transfer_buffer)
            #print("usb_req:", vars(usb_req))

            self.sony_ericsson.handle_out(usb_req)

    def handle_get_descriptor(self, usb_req, control_req):
        wValue = control_req.wValue

        descriptor_type  = (wValue & 0xff00) >> 8
        descriptor_index = (wValue & 0x00ff)

        print(f"GET_DESCRIPTOR({DESCRIPTOR_TYPES.get(descriptor_type)}, "
              f"0x{descriptor_index:02x})")

        if descriptor_type == DESCRIPTOR_DEVICE:
            self.send_usb_ret(usb_req, self.device_descriptor.pack())

        elif descriptor_type == DESCRIPTOR_CONFIGURATION:
            self.send_usb_ret(usb_req, self.all_configurations[:control_req.wLength])

        elif descriptor_type == DESCRIPTOR_STRING:
            if descriptor_index in self.usb_strings:
                self.send_usb_ret(usb_req, self.usb_strings[descriptor_index])
            else:
                # Not found
                # Send STALL
                print("\033[31mUNHANDLED STRING\033[0m")
                self.send_usb_ret(usb_req, b"", usb_len=0, status=-errno.EPIPE)

        elif descriptor_type == DESCRIPTOR_DEVICE_QUALIFIER:
            # Send STALL
            self.send_usb_ret(usb_req, b"", usb_len=0, status=-errno.EPIPE)

        elif descriptor_type == DESCRIPTOR_DEVICE:
            # Send STALL
            self.send_usb_ret(usb_req, b"", usb_len=0, status=-errno.EPIPE)

        else:
            raise Exception("Unhandled GET_DESCRIPTOR")

    def handle_usb_control(self, usb_req):
        control_req = StandardDeviceRequest.from_bytes(usb_req.setup)

        print()
        print("\033[31m=== Control request: ===\033[0m")
        print("usb_req:", vars(usb_req))
        print("control_req:", vars(control_req))
        print(f"bmRequestType: {hex(control_req.bmRequestType)}")
        print(f"bRequest: {hex(control_req.bRequest)}")
        print(f"wValue: {hex(control_req.wValue)}")

        if control_req.bmRequestType == USB_CTRL_IN:
            # Control request (device -> host)
            if control_req.bRequest == CTRL_GET_STATUS:
                # GET_STATUS
                self.send_usb_ret(usb_req, b"\x00\x00")

            elif control_req.bRequest == CTRL_GET_DESCRIPTOR:
                # GET_DESCRIPTOR
                self.handle_get_descriptor(usb_req, control_req)

            elif control_req.bRequest == CTRL_GET_CONFIGURATION:
                # GET_CONFIGURATION
                self.send_usb_ret(usb_req, b"\x00")

            else:
                raise Exception("Unhandled control device -> host request")

        elif control_req.bmRequestType == USB_CTRL_OUT:
            # Control request (host -> device)
            if control_req.bRequest == CTRL_SET_CONFIGURATION:
                print(f"handle_set_configuration {control_req.wValue:n}")
                self.send_usb_ret(usb_req, b'', 0)

            else:
                raise Exception("Unhandled control host -> device request")

        else:
            raise Exception("Unhandled control request type")

def main():
    usb_dev = USBSE()
    usb_container = USBContainer()
    usb_container.add_usb_device(usb_dev)  # Supports only one device!
    usb_container.run(debug=0)

if __name__ == "__main__":
    main()
