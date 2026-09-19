
import socket
import struct
from common import BaseStructure, BaseStructureData
from abc import ABC, abstractmethod

USBIP_DIR_OUT = 0
USBIP_DIR_IN = 1

class USBIPHeader(BaseStructure):
    _byte_order_ = '>'  # USBIP uses big-endian
    _fields_ = [
        ('version', 'H', 0x0111),  # USB/IP version 1.1.1
        ('command', 'H'),
        ('status', 'I')
    ]


class USBInterface(BaseStructure):
    _byte_order_ = '>'
    _fields_ = [
        ('bInterfaceClass', 'B'),
        ('bInterfaceSubClass', 'B'),
        ('bInterfaceProtocol', 'B'),
        ('align', 'B', 0)
    ]


class OP_REP_DevList(BaseStructure):
    _byte_order_ = '>'
    _fields_ = [
        ('base', USBIPHeader()),
        ('nExportedDevice', 'I'),
        ('usbPath', '256s'),
        ('busID', '32s'),
        ('busnum', 'I'),
        ('devnum', 'I'),
        ('speed', 'I'),
        ('idVendor', 'H'),
        ('idProduct', 'H'),
        ('bcdDevice', 'H'),
        ('bDeviceClass', 'B'),
        ('bDeviceSubClass', 'B'),
        ('bDeviceProtocol', 'B'),
        ('bConfigurationValue', 'B'),
        ('bNumConfigurations', 'B'),
        ('bNumInterfaces', 'B'),
        ('interfaces', USBInterface())
    ]


class OP_REP_Import(BaseStructure):
    _byte_order_ = '>'
    _fields_ = [
        ('base', USBIPHeader()),
        ('usbPath', '256s'),
        ('busID', '32s'),
        ('busnum', 'I'),
        ('devnum', 'I'),
        ('speed', 'I'),
        ('idVendor', 'H'),
        ('idProduct', 'H'),
        ('bcdDevice', 'H'),
        ('bDeviceClass', 'B'),
        ('bDeviceSubClass', 'B'),
        ('bDeviceProtocol', 'B'),
        ('bConfigurationValue', 'B'),
        ('bNumConfigurations', 'B'),
        ('bNumInterfaces', 'B')
    ]

USBIP_CMD_SUBMIT = 0x01
USBIP_RET_SUBMIT = 0x03

USBIP_CMD_UNLINK = 0x02
USBIP_RET_UNLINK = 0x04

class USBIP_RET_Submit(BaseStructureData):
    _byte_order_ = '>'
    _fields_ = [
        ('command', 'I', USBIP_RET_SUBMIT),
        ('seqnum', 'I'),
        ('devid', 'I', 0),
        ('direction', 'I', 0),
        ('ep', 'I', 0),
        ('status', 'i'),
        ('actual_length', 'I'),
        ('start_frame', 'I', 0),
        ('number_of_packets', 'I', 0xffffffff),
        ('error_count', 'I'),
        ('padding', 'Q', 0)
    ]
    _data_field_ = "data"

class USBIP_RET_Unlink(BaseStructure):
    _byte_order_ = '>'
    _fields_ = [
        ('command', 'I', USBIP_RET_UNLINK),
        ('seqnum', 'I'),
        ('devid', 'I', 0),
        ('direction', 'I', 0),
        ('ep', 'I', 0),
        ('status', 'i'),
        ('padding', '24s', b"\x00"*24),
    ]

class USBIP_Header_Basic(BaseStructure):
    _byte_order_ = '>'
    _fields_ = [
        ('command', 'I'),
        ('seqnum', 'I'),
        ('devid', 'I'),
        ('direction', 'I'),
        ('ep', 'I'),  # endpoint
    ]

class USBIP_CMD_Submit(BaseStructure):
    _byte_order_ = '>'
    _fields_ = [
        ('command', 'I'),
        ('seqnum', 'I'),
        ('devid', 'I'),
        ('direction', 'I'),
        ('ep', 'I'),  # endpoint
        ('transfer_flags', 'I'),
        ('transfer_buffer_length', 'I'),
        ('start_frame', 'I'),
        ('number_of_packets', 'I'),
        ('interval', 'I'),
        ('setup', '8s')
    ]

class USBIP_CMD_Unlink(BaseStructure):
    _byte_order_ = '>'
    _fields_ = [
        ('command', 'I'),
        ('seqnum', 'I'),
        ('devid', 'I'),
        ('direction', 'I'),
        ('ep', 'I'),  # endpoint
        ('unlink_seqnum', 'I'),
        ('padding', '24s', b"\x00"*24),
    ]

class StandardDeviceRequest(BaseStructure):
    _byte_order_ = '<'  # USB uses little-endian
    _fields_ = [
        ('bmRequestType', 'B'),
        ('bRequest', 'B'),
        ('wValue', 'H'),
        ('wIndex', 'H'),
        ('wLength', 'H')
    ]


class DeviceDescriptor(BaseStructure):
    _byte_order_ = '<'
    _fields_ = [
        ('bLength', 'B', 18),
        ('bDescriptorType', 'B', 1),
        ('bcdUSB', 'H', 0x0110),
        ('bDeviceClass', 'B'),
        ('bDeviceSubClass', 'B'),
        ('bDeviceProtocol', 'B'),
        ('bMaxPacketSize0', 'B'),
        ('idVendor', 'H'),
        ('idProduct', 'H'),
        ('bcdDevice', 'H'),
        ('iManufacturer', 'B', 0),
        ('iProduct', 'B', 0),
        ('iSerialNumber', 'B', 0),
        ('bNumConfigurations', 'B')
    ]


class DeviceConfiguration(BaseStructure):
    _byte_order_ = '<'
    _fields_ = [
        ('bLength', 'B', 9),
        ('bDescriptorType', 'B', 2),
        ('wTotalLength', 'H'),
        ('bNumInterfaces', 'B'),
        ('bConfigurationValue', 'B', 1),
        ('iConfiguration', 'B', 0),
        ('bmAttributes', 'B', 0x80),
        ('bMaxPower', 'B')
    ]


class BOSDescriptor(BaseStructure):
    _byte_order_ = '<'
    _fields_ = [
        ('bLength', 'B', 0x05),
        ('bDescriptorType', 'B', 0x0F),  # Binary Device Object Store (BOS) Descriptor
        ('wTotalLength', 'H'),
        ('bNumDeviceCaps', 'B'),
    ]


class DeviceQualifierDescriptor(BaseStructure):
    _byte_order_ = '<'
    _fields_ = [
        ('bLength', 'B', 0x0a),
        ('bDescriptorType', 'B', 0x06),  # Device Qualifier Descriptor
        ('bcdUSB', 'H'),
        ('bDeviceClass', 'B'),
        ('bDeviceSubClass', 'B'),
        ('bDeviceProtocol', 'B'),
        ('bMaxPacketSize0', 'B'),
        ('bNumConfigurations', 'B'),
        ('bReserved', 'B', 0),
    ]


class InterfaceDescriptor(BaseStructure):
    _byte_order_ = '<'
    _fields_ = [
        ('bLength', 'B', 9),
        ('bDescriptorType', 'B', 4),
        ('bInterfaceNumber', 'B', 0),
        ('bAlternateSetting', 'B', 0),
        ('bNumEndpoints', 'B', 1),
        ('bInterfaceClass', 'B'),
        ('bInterfaceSubClass', 'B'),
        ('bInterfaceProtocol', 'B'),
        ('iInterface', 'B', 0)
    ]


class EndpointDescriptor(BaseStructure):
    _byte_order_ = '<'
    _fields_ = [
        ('bLength', 'B', 7),
        ('bDescriptorType', 'B', 0x5),
        ('bEndpointAddress', 'B'),
        ('bmAttributes', 'B'),
        ('wMaxPacketSize', 'H'),
        ('bInterval', 'B')
    ]


class USBRequest():
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class USBDevice(ABC):
    '''
    Abstract Base Class
    '''

    @property
    @abstractmethod
    def configurations(self): pass

    @property
    @abstractmethod
    def device_descriptor(self): pass

    def __init__(self):
        self.generate_raw_configuration()

    def generate_raw_configuration(self):
        all_configurations = bytearray()
        for configuration in self.configurations:
            cur_config = bytearray()

            for interface in configuration.interfaces:
                for interface_alternative in interface:
                    cur_config.extend(interface_alternative.pack())
                    if hasattr(interface_alternative, 'class_descriptor'):
                        cur_config.extend(interface_alternative.class_descriptor.pack())
                    for endpoint in interface_alternative.endpoints:
                        cur_config.extend(endpoint.pack())
                        if hasattr(endpoint, 'class_descriptor'):
                            cur_config.extend(endpoint.class_descriptor.pack())

            configuration.wTotalLength = configuration.size() + len(cur_config)
            all_configurations.extend(configuration.pack() + cur_config)

        self.all_configurations = all_configurations

    def send_usb_ret(self, usb_req, usb_res, usb_len=None, status=0):
        debug_msg = f"Sending {bytes(usb_res)}"
        if status != 0:
            debug_msg += f" status={status}"

        if usb_req.direction == USBIP_DIR_IN or status != 0:
            print(debug_msg)

        if usb_len is None:
            usb_len = len(usb_res)

        self.connection.sendall(USBIP_RET_Submit(command=USBIP_RET_SUBMIT,
                                                 seqnum=usb_req.seqnum,
                                                 status=status,
                                                 actual_length=usb_len,
                                                 data=usb_res).pack())

    def handle_usb_request(self, usb_req):
        if usb_req.ep == 0:  # Endpoint 0 is always the control endpoint
            self.handle_usb_control(usb_req)
        else:
            self.handle_data(usb_req)

    @abstractmethod
    def handle_usb_unlink(self, unlink_seqnum) -> int:
        # Needs to respond with the status
        pass

    @abstractmethod
    def handle_data(self, usb_req):
        pass

    @abstractmethod
    def handle_usb_control(self, usb_req):
        pass


def bytes_to_string(bytes):
    if bytes:
        return ''.join(["\\x{0:02x}".format(val) for val in bytes])
    return None


class USBContainer:
    usb_devices = []

    def add_usb_device(self, usb_device):
        self.usb_devices.append(usb_device)

    def handle_attach(self):
        usb_dev = self.usb_devices[0]
        device_descriptor = usb_dev.device_descriptor
        return OP_REP_Import(base=USBIPHeader(command=3, status=0),
                             usbPath='/sys/devices/pci0000:00/0000:00:01.2/usb1/1-1'.encode('ascii'),
                             busID='1-1'.encode('ascii'),
                             busnum=1,
                             devnum=2,
                             speed=2,
                             idVendor=device_descriptor.idVendor,
                             idProduct=device_descriptor.idProduct,
                             bcdDevice=device_descriptor.bcdDevice,
                             bDeviceClass=device_descriptor.bDeviceClass,
                             bDeviceSubClass=device_descriptor.bDeviceSubClass,
                             bDeviceProtocol=device_descriptor.bDeviceProtocol,
                             bConfigurationValue=usb_dev.configurations[0].bConfigurationValue,
                             bNumConfigurations=device_descriptor.bNumConfigurations,
                             bNumInterfaces=usb_dev.configurations[0].bNumInterfaces)

    def handle_device_list(self):
        usb_dev = self.usb_devices[0]
        device_descriptor = usb_dev.device_descriptor
        return OP_REP_DevList(base=USBIPHeader(command=5, status=0),
                              nExportedDevice=1,
                              usbPath='/sys/devices/pci0000:00/0000:00:01.2/usb1/1-1'.encode('ascii'),
                              busID='1-1'.encode('ascii'),
                              busnum=1,
                              devnum=2,
                              speed=2,
                              idVendor=device_descriptor.idVendor,
                              idProduct=device_descriptor.idProduct,
                              bcdDevice=device_descriptor.bcdDevice,
                              bDeviceClass=device_descriptor.bDeviceClass,
                              bDeviceSubClass=device_descriptor.bDeviceSubClass,
                              bDeviceProtocol=device_descriptor.bDeviceProtocol,
                              bConfigurationValue=usb_dev.configurations[0].bConfigurationValue,
                              bNumConfigurations=device_descriptor.bNumConfigurations,
                              bNumInterfaces=usb_dev.configurations[0].bNumInterfaces,
                              interfaces=USBInterface(bInterfaceClass=usb_dev.configurations[0].interfaces[0][0].bInterfaceClass,
                                                      bInterfaceSubClass=usb_dev.configurations[0].interfaces[0][0].bInterfaceSubClass,
                                                      bInterfaceProtocol=usb_dev.configurations[0].interfaces[0][0].bInterfaceProtocol))

    def run(self, ip='127.0.0.1', port=3240, debug=False):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ip, port))
        s.listen()
        attached = False
        while 1:
            conn, addr = s.accept()
            print('Connection address:', addr)
            while 1:
                if not attached:
                    data = conn.recv(8)
                    if not data:
                        break
                    req = USBIPHeader.from_bytes(data)
                    print('Header Packet')
                    print('command:', hex(req.command))
                    if req.command == 0x8005:  # OP_REQ_DEVLIST
                        print('list of devices')
                        conn.sendall(self.handle_device_list().pack())
                    elif req.command == 0x8003:  # OP_REQ_IMPORT
                        print('attach device')
                        conn.recv(32)  # receive bus id
                        conn.sendall(self.handle_attach().pack())
                        attached = True
                else:
                    if debug:
                        print('\n=== Got request ===')

                    # Recv header
                    header_data = bytearray(conn.recv(USBIP_Header_Basic.size()))
                    header_basic = USBIP_Header_Basic.from_bytes(header_data)

                    if debug:
                        print(f"Command: {header_basic.command}")

                    # Here we've just received the USBIP_Header_Basic

                    if header_basic.command == USBIP_CMD_SUBMIT:
                        # USBIP_CMD_SUBMIT
                        header_data.extend(conn.recv(USBIP_CMD_Submit.size() - header_basic.size()))
                        cmd = USBIP_CMD_Submit.from_bytes(header_data)

                        if debug:
                            print(header_data)

                        transfer_buffer = conn.recv(cmd.transfer_buffer_length) if cmd.direction == USBIP_DIR_OUT else None

                        if debug:
                            print(f"usbip cmd {cmd.command:x}")
                            print(f"usbip seqnum {cmd.seqnum:x}")
                            print(f"usbip devid {cmd.devid:x}")
                            print(f"usbip direction {cmd.direction:x}")
                            print(f"usbip ep {cmd.ep:x}")
                            print(f"usbip flags {cmd.transfer_flags:x}")
                            print(f"usbip transfer buffer length {cmd.transfer_buffer_length:x}")
                            print(f"usbip start {cmd.start_frame:x}")
                            print(f"usbip number of packets {cmd.number_of_packets:x}")
                            print(f"usbip interval {cmd.interval:x}")
                            print(f"usbip setup {bytes_to_string(cmd.setup)}")
                            print(f"usbip transfer buffer {bytes_to_string(transfer_buffer)}")

                        usb_req = USBRequest(seqnum=cmd.seqnum,
                                             devid=cmd.devid,
                                             direction=cmd.direction,
                                             ep=cmd.ep,
                                             flags=cmd.transfer_flags,
                                             numberOfPackets=cmd.number_of_packets,
                                             interval=cmd.interval,
                                             setup=cmd.setup,
                                             transfer_buffer=transfer_buffer)
                        self.usb_devices[0].connection = conn
                        self.usb_devices[0].handle_usb_request(usb_req)

                    elif header_basic.command == USBIP_CMD_UNLINK:
                        header_data.extend(conn.recv(cmd.size() - header_basic.size()))
                        cmd = USBIP_CMD_Unlink.from_bytes(header_data)

                        if debug:
                            print(header_data)
                            print(f"usbip unlink_seqnum {cmd.unlink_seqnum}")

                        self.usb_devices[0].connection = conn
                        ret = self.usb_devices[0].handle_usb_unlink(cmd.unlink_seqnum)

                        conn.sendall(USBIP_RET_Unlink(command=USBIP_RET_UNLINK,
                                                      seqnum=cmd.seqnum,
                                                      status=ret).pack())

                    else:
                        raise Exception("Unknown usbip command!")

            print('Close connection\n')
            conn.close()
