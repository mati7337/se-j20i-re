import usb.core
import usb.util
import time
import argparse
import os

import EMPProto

EMULATED_USB_BUS = 7

class Client:
    # Very minimal client, it allows for writing and reading usb bulk messages
    # using the two IN and OUT endpoints provided by the service mode

    # This class is pretty much what the Gordon's Gate driver does

    DEFAULT_TIMEOUT = 1000

    def __init__(self,
                 dev,
                 ep_in=EMPProto.USB_EP_IN,
                 ep_out=EMPProto.USB_EP_OUT):
        self.dev = dev

        # Set configuration causes the hello message to be skipped
        #self.dev.set_configuration()

        self.cfg = self.dev.get_active_configuration()
        self.intf = self.cfg[(0, 0)]

        self.ep_out = usb.util.find_descriptor(
            self.intf,
            custom_match=lambda e: e.bEndpointAddress == ep_out
        )
        self.ep_in = usb.util.find_descriptor(
            self.intf,
            custom_match=lambda e: e.bEndpointAddress == ep_in
        )

    def write(self, data, timeout=DEFAULT_TIMEOUT):
        return self.ep_out.write(data, timeout)

    def read(self, size, timeout=DEFAULT_TIMEOUT):
        return bytes(self.ep_in.read(size, timeout))

    def read_var_len(self):
        # Read the weird variable length encoding used for some commands
        # Format: 0x63 LENGTH
        out = bytearray()

        while len(out) < 2:
            out.extend(self.read(4096))

        if out[0] != EMPProto.VAR_LEN_MSG_MAGIC:
            raise EMPProto.ProtocolError(f"Invalid var length message magic: {out[0]}")

        expected_size = out[1]

        while len(out) < expected_size:
            out.extend(self.read(4096))

        return bytes(out)

class Cli:
    def __init__(self):
        self.dev = None
        self.client = None
        self.strict = False
        self.find_emulated = True

    def find_sony_ericsson(self):
        devs = usb.core.find(idVendor=0x0fce, idProduct=0xadde, find_all=1)

        for dev in devs:
            if dev.bus == EMULATED_USB_BUS and self.find_emulated:
                return dev
            elif dev.bus != EMULATED_USB_BUS and not self.find_emulated:
                return dev

        return None

    def enumerate_dev_strings(self):
        for i in range(256):
            try:
                data = self.dev.ctrl_transfer(usb.util.CTRL_IN, 0x06,
                                              wValue=(usb.util.DESC_TYPE_STRING << 8) | i,
                                              wIndex=0x0409,
                                              data_or_wLength=254)

                if data[1] == usb.util.DESC_TYPE_STRING:
                    # STRING
                    print(hex(i), bytes(data)[2:].decode("utf-16le", errors="surrogateescape"))
                else:
                    print(hex(i), bytes(data))
            except usb.core.USBError:
                pass

    def get_device(self):
        print("Looking for device")
        while 1:
            self.dev = self.find_sony_ericsson()
            if self.dev:
                break
            time.sleep(0.5)

        print(f"Found Bus {self.dev.bus} Device {self.dev.address}")

        self.client = Client(self.dev)

    def read_hello(self):
        # Read hello message
        hello = None

        try:
            hello = self.client.read(4096)
        except usb.core.USBTimeoutError:
            # We could probably ignore the hello message, but
            # just to be sure replug the device
            print("Reading hello message timed out!")
            if self.strict:
                print("Please unplug then replug the device")
                raise EMPProto.ProtocolError("Expected a hello message")

        if hello:
            print("Got hello:", hello)

            if hello != EMPProto.HELLO_RESP:
                raise EMPProto.ProtocolError(
                    "Invalid hello message! "
                    f"Expected {EMPProto.HELLO_RESP}, got {hello}."
                )

    def get_ident(self):
        print(f"> {EMPProto.CMD_IDENT.decode()} (CMD_IDENT)")
        data = self.client.write(EMPProto.CMD_IDENT)
        ident = EMPProto.RespIdent.from_bytes(self.client.read(4096))

        if ident.chip_id in EMPProto.CHIP_IDS:
            print(f"Chip id: {EMPProto.CHIP_IDS[ident.chip_id]} (0x{ident.chip_id:04x})")
        else:
            raise EMPProto.ProtocolError(f"Unknown chip_id 0x{ident.chip_id:04x}")

        if ident.emp_protocol == EMPProto.EMPPROTO_VER:
            print(f"EMP protocol: 0x{ident.emp_protocol:04x}")
        else:
            raise EMPProto.ProtocolError(f"Unknown emp_protocol version 0x{ident.emp_protocol}")

        return ident

    def get_otp(self):
        print(f"> {EMPProto.CMD_READ_OTP.decode()} (CMD_READ_OTP)")
        self.client.write(EMPProto.CMD_READ_OTP)
        otp = EMPProto.RespReadOTP.from_bytes(self.client.read_var_len())
        print(otp)
        return otp

    def get_erom_color(self):
        print(f"> {EMPProto.CMD_READ_EROM_COLOR.decode()} (CMD_READ_EROM_COLOR)")
        self.client.write(EMPProto.CMD_READ_EROM_COLOR)
        erom_color = EMPProto.RespReadEromColor.from_bytes(self.client.read_var_len())
        print(erom_color)
        print("Color:", EMPProto.EROM_COLORS.get(erom_color.color, erom_color.color))
        return erom_color

    def get_erom_cid(self):
        print(f"> {EMPProto.CMD_READ_EROM_CID.decode()} (CMD_READ_EROM_CID)")
        self.client.write(EMPProto.CMD_READ_EROM_CID)
        erom_cid = EMPProto.RespReadEromCid.from_bytes(self.client.read_var_len())
        print(erom_cid)
        print("EROM CID:", erom_cid.cid)
        return erom_cid

    def get_erom_var(self, unita, unitb):
        req = EMPProto.CMDReadEromVar(unita=unita, unitb=unitb)
        req_raw = req.pack()

        #print(f"> {req_raw} (CMD_READ_EROM_VAR({unita:02x}/{unitb:04x}))")
        self.client.write(req_raw)

        erom_var = EMPProto.RespReadEromVar.from_bytes(self.client.read(4096))

        #data = raw_resp[erom_var_header.size():]
        assert len(erom_var.data) == erom_var.length
        assert unita == erom_var.unita
        assert unitb == erom_var.unitb

        return erom_var

    def send_k(self):
        # TODO reverse
        print(f"> {EMPProto.CMD_K.decode()} (CMD_K)")
        self.client.write(EMPProto.CMD_K)
        data = self.client.read(4096)
        print(data)
        return data

    def read_q_msg(self):
        packet = self.client.read(4096)
        print("Got", packet)

        header = EMPProto.QHeader.from_bytes(packet)

        assert header.magic == b"\xaa\xfb\xee\xee\x00"

        size_left = header.length + 1
        output = bytearray(packet[header.size():])
        size_left -= len(output)

        while size_left > 0:
            packet = self.client.read(4096)
            print("Got", packet)
            output.extend(packet)
            size_left -= len(packet)

        assert not size_left < 0

        print("Got Q message:", header)
        print(bytes(output))

        return header, bytes(output)

    def send_q_msg(self, unknown, data, part_size=64):
        header = EMPProto.QHeader(length=len(data)-1, unknown=unknown)
        to_send = header.pack() + data

        offset = 0
        while offset < len(to_send):
            offset += self.client.write(to_send[offset:offset + part_size])

    def switch_mode_q(self):
        # TODO reverse
        print(f"> {EMPProto.CMD_SWITCH_MODE_Q.decode()} (CMD_SWITCH_MODE_Q)")
        self.client.write(EMPProto.CMD_SWITCH_MODE_Q)

        # Now phone should be in Q mode
        # and respond with an automatic message (maybe some hello?)
        return

    def get_semcboot_ver(self):
        print(f"> {EMPProto.CMD_READ_SEMCBOOT_VER.decode()} (CMD_READ_SEMCBOOT_VER)")
        self.client.write(EMPProto.CMD_READ_SEMCBOOT_VER)

        resp = EMPProto.RespReadSemcbootVer.from_bytes(
            self.client.read_var_len()
        )

        assert len(resp.data) == resp.length

        print(resp.data.decode())

        return resp

    def send_cmd(self, cmd):
        # send a cmd and print response
        print(f"> {cmd.decode()}")
        self.client.write(cmd)

        data = self.client.read(4096)
        print(data)
        data = self.client.read(4096)
        print(data)

        return data

    # CLI Commands

    def test(self, args):
        with open("certs/db3350_cid81-80-53-52-51-49-0_sefp2.babe", "rb") as fl:
            # x509 certificate with the babe header
            db3350_cert_babe = fl.read()

        #with open("loaders/db3350_cid81_red.bin", "rb") as fl:
        #    db3350_loader = fl.read()

        #with open("loaders/db3350_cid81_red.bin.3", "rb") as fl:
        #    db3350_loader3 = fl.read()

        self.get_device()
        self.read_hello()

        ident = self.get_ident()
        k = self.send_k()
        otp = self.get_otp()
        color = self.get_erom_color()
        #self.send_cmd(b"IC40")
        erom_cid = self.get_erom_cid()
        var1 = self.get_erom_var(0x02, 0x1062)
        #self.send_cmd(b"ICE0")
        semcboot_ver = self.get_semcboot_ver()

        # Switch to Q mode
        q = self.switch_mode_q()
        q_header, q_data = self.read_q_msg()
        print("> Sending ???")
        # Maybe the echo message? Like for confirming success idk
        self.send_q_msg(0x04, b'\x00\xa8\x6c')

        return

        print("> Sending certificate")
        self.send_q_msg(0x01, db3350_cert_babe) # Send certificate
        q_header, q_data = self.read_q_msg()

        #return

        time.sleep(2) # IDK if needed, but just to make sure

        print("> Sending loader")
        self.send_q_msg(0x02, db3350_loader) # Send loader
        q_header, q_data = self.read_q_msg()

        time.sleep(1)
        #print(self.client.read(4096))

        #return

        print("> Sending loader 0x03")
        self.send_q_msg(0x03, db3350_loader3) # Send loader ???
        print("a")
        #time.sleep(1)
        q_header, q_data = self.read_q_msg()

        # uhh, maybe?
        time.sleep(0.2)
        self.get_device()

        #print("reading")
        print("b")
        #time.sleep(1)
        print(self.client.read(4096, timeout=20000))
        print("c")
        #time.sleep(1)
        print(self.client.read(4096, timeout=2000))
        #self.send_cmd(b"Q")

    def read_erom(self, args):
        unita = int(args.unita, 16)
        unitb = int(args.unitb, 16)

        self.get_device()
        self.read_hello()

        self.get_ident()
        self.get_erom_var(unita, unitb)

    def enumerate_erom(self, args):
        # Read all possible erom units
        # Print non empty ones
        self.get_device()
        self.read_hello()

        self.get_ident()

        if args.outdir and not os.path.isdir(args.outdir):
            raise ValueError(f"{args.outdir} is not a directory!")

        # unita doesn't seem to matter
        unita = 0

        for unitb in range(0xffff):
            var = self.get_erom_var(unita, unitb)

            if var.length != 0:
                print(f"\033[32m{unita:02x}/{unitb:04x} Found\033[0m")
                print(var.data)

                if args.outdir:
                    with open(f"{args.outdir}/var_{unitb:04x}.bin", "wb") as fl:
                        fl.write(var.data)

            else:
                print(f"\033[31m{unita:02x}/{unitb:04x} - 404\033[0m")

    def main(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--emu", action="store_true", help="Only find emulated devices")

        subparsers = parser.add_subparsers(dest="command", required=True)

        test_parser = subparsers.add_parser("test", help="Run the test function")
        test_parser.set_defaults(func=self.test)

        enum_erom_parser = subparsers.add_parser("enum-erom", help="Find all non empty erom variables")
        enum_erom_parser.add_argument("--outdir", type=str, help="Output directory")
        enum_erom_parser.set_defaults(func=self.enumerate_erom)

        read_erom_parser = subparsers.add_parser("read-erom", help="Read an EROM variable")
        read_erom_parser.add_argument("unita", type=str)
        read_erom_parser.add_argument("unitb", type=str)
        read_erom_parser.set_defaults(func=self.read_erom)

        args = parser.parse_args()
        self.find_emulated = args.emu
        args.func(args)

if __name__ == "__main__":
    cli = Cli()
    cli.main()
