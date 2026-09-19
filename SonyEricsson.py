import EMPProto
from collections import deque
import SonyEricssonConfig

# Response to a usb_req, allows specifying the status code in addition to data
class USBResponse():
    def __init__(self, data, status=0):
        self.data = data
        self.status = status

MODE_NORMAL = 0  # Regular commands
MODE_Q = 1       # After sending the Q command in normal mode
MODE_UNKNOWN = 2 # Unknown state - use for debugging, it just prints what it receives

# Actual device handling IN and OUT usb packets
class SonyEricsson():
    def __init__(self, usb, Config=SonyEricssonConfig.SonyEricssonTest):
        self.usb = usb
        self.config = Config()

        self.send_usb_ret = self.usb.send_usb_ret

        self.usb_req_queue = deque()
        self.send_queue = deque([USBResponse(self.config.hello_message)])

        self.mode = MODE_NORMAL

        self.q_header = None
        self.q_current = bytearray()
        self.q_current_left = 0
        self.q_image = {}
        self.q_is_receiving = False

    def send_data(self):
        # Send stuff from the send queue to IN requests from usb_req queue
        while len(self.usb_req_queue) and len(self.send_queue):
            to_send = self.send_queue.popleft()
            usb_req = self.usb_req_queue.popleft()
            self.send_usb_ret(usb_req, to_send.data, status=to_send.status)

    def handle_in(self, usb_req):
        # device -> host
        self.usb_req_queue.append(usb_req)
        self.send_data()

    def handle_out_unknown_mode(self, usb_req):
        # Unknown state, just print what you get
        print("> UNKNOWN MODE RECV DATA")
        data = usb_req.transfer_buffer

        print(data)

        self.send_data()

    def handle_out_q_mode(self, usb_req):
        # Q mode - read loaders
        print("> Q MODE RECV DATA")
        data = usb_req.transfer_buffer

        if self.q_current_left < 0:
            raise ValueError(f"q_current_left={self.q_current_left} < 0")

        if not self.q_is_receiving:
            # Receive new package
            if data.startswith(b"\xaa\x06"):
                # TODO: reverse and check with real device
                print("Weird package")
                # TODO: this is fucked
                print(data)
                print("Sending 2 ACKs")
                for i in range(2):
                    self.send_queue.append(USBResponse(EMPProto.RESP_Q_ACK))

            elif data.startswith(b"\xaa\xfb\xee\xee\x00"):
                # Regular Q header
                header = EMPProto.QHeader.from_bytes(data)
                assert header.magic == b"\xaa\xfb\xee\xee\x00"
                print("Receiving new package")
                self.q_is_receiving = True
                self.q_header = header
                print(header)

                self.q_current_left = header.length + 1

                self.q_current.extend(data[header.size():])
                self.q_current_left -= len(data) - header.size()

        else:
            # Receive the rest of the current package
            self.q_current.extend(data)
            self.q_current_left -= len(data)

        # Handle the whole Q package
        if self.q_is_receiving and self.q_current_left == 0:
            print("RECEIVED")
            print(self.q_header)
            print(self.q_current)

            if self.q_header.unknown == 0x01: # Image header
                print("Sending ACK")
                self.send_queue.append(USBResponse(EMPProto.RESP_Q_ACK))

                assert len(self.q_image.get(0x01, b"")) == 0

                self.q_image[0x01] = self.q_current.copy()

            elif self.q_header.unknown in [0x01, 0x02]: # Image header, Image payload
                print("Sending ACK")
                self.send_queue.append(USBResponse(EMPProto.RESP_Q_ACK))

                if not 0x02 in self.q_image:
                    self.q_image[0x02] = bytearray()

                self.q_image[0x02].extend(self.q_current)

            elif self.q_header.unknown == 0x03: # Image end
                print("Sending ACK")
                self.send_queue.append(USBResponse(EMPProto.RESP_Q_ACK))
                self.q_image[0x03] = self.q_current.copy()

                print("\033[31mGOT THE WHOLE IMAGE\033[0m")
                print("HEADER:")
                print(bytes(self.q_image[0x01]))
                print("PAYLOAD:")
                print(bytes(self.q_image[0x02]))
                print("END:")
                print(bytes(self.q_image[0x03]))

                self.q_image.clear()

                # Another ACK for successful image load
                print("Sending ACK")
                self.send_queue.append(USBResponse(EMPProto.RESP_Q_ACK))

                # Maybe then another mode?
                #for i in range(10):
                #    self.send_queue.append(USBResponse(EMPProto.RESP_Q_ACK))
                #self.mode = MODE_SEFP2_LOADER

                #for i in range(10):
                #    self.send_queue.append(USBResponse(header.pack() + resp))

                # Maybe loader?
                #self.mode = MODE_SEFP2_LOADER

            elif self.q_header.unknown == 0x04: # Set ACK???
                print("Set ACK?")
                print(self.q_header, self.q_current)

            self.q_is_receiving = False
            self.q_current.clear()
            self.q_header = None

        self.send_data()

    def handle_out_normal_mode(self, usb_req):
        # Normal command mode
        data = usb_req.transfer_buffer

        # Handle commands
        if data == EMPProto.CMD_IDENT:
            print("> IDENT")
            resp = EMPProto.RespIdent(
                chip_id=self.config.chip_id,
                emp_protocol=EMPProto.EMPPROTO_VER
            )
            print("Responding", resp)
            self.send_queue.append(USBResponse(resp.pack()))

        elif data == EMPProto.CMD_K:
            print("> K")
            resp = EMPProto.RESP_K
            print("Responding", resp)
            self.send_queue.append(USBResponse(resp))

        elif data == EMPProto.CMD_READ_OTP:
            print("> READ_OTP")
            resp = EMPProto.RespReadOTP(
                    cid=self.config.cid_otp,
                    imei=self.config.imei
            )
            print("Responding", resp)
            # For some reason READ_OTP is sent as a single packet [...]
            self.send_queue.append(USBResponse(resp.pack()))

        elif data == EMPProto.CMD_READ_EROM_COLOR:
            print("> READ_EROM_COLOR")
            resp = EMPProto.RespReadEromColor(
                    color=self.config.erom_color
            )
            print("Responding", resp)
            # [...] while the rest of variable length messages is sent as 2 packets
            resp_raw = resp.pack()
            self.send_queue.append(USBResponse(resp_raw[:2]))
            self.send_queue.append(USBResponse(resp_raw[2:]))

        elif data == EMPProto.CMD_READ_EROM_CID:
            print("> READ_EROM_CID")
            resp = EMPProto.RespReadEromCid(
                    cid=self.config.cid_erom
            )
            print("Responding", resp)
            resp_raw = resp.pack()
            self.send_queue.append(USBResponse(resp_raw[:2]))
            self.send_queue.append(USBResponse(resp_raw[2:]))

        elif data == EMPProto.CMD_READ_SEMCBOOT_VER:
            print("> READ_SEMCBOOT_VER")
            print(self.config.semcboot_ver)
            resp = EMPProto.RespReadSemcbootVer(
                length=len(self.config.semcboot_ver),
                data=self.config.semcboot_ver
            )
            self.send_queue.append(USBResponse(resp.pack_header()))
            self.send_queue.append(USBResponse(resp.data))

        elif data[:4] == EMPProto.CMD_READ_EROM_VAR:
            print("> READ_EROM_VAR")
            req = EMPProto.CMDReadEromVar.from_bytes(data)
            print("Request", req)

            var_data = self.config.erom.get(req.unita, req.unitb)
            print(f"{req.unita:02x}/{req.unitb:04x} = {var_data}")

            var_resp = EMPProto.RespReadEromVar(unita=req.unita,
                                                  unitb=req.unitb,
                                                  length=len(var_data),
                                                  data=var_data)

            self.send_queue.append(USBResponse(var_resp.pack()))

        elif data == EMPProto.CMD_SWITCH_MODE_Q:
            print("> Q")
            resp = EMPProto.QMessage(unknown=0x05, data=b"\x88\xeb")
            print("Responding", resp)
            self.send_queue.append(USBResponse(resp.pack()))

            print("\033[32mSWITCHING MODE TO Q\033[0m")
            self.mode = MODE_Q

        else:
            print(f"\033[31m> Unknown command: {data}\033[0m")
            #raise Exception("Unknown command")

        self.send_data()

    def handle_out(self, usb_req):
        # host -> device

        # Got the command
        self.send_usb_ret(usb_req, b'', len(usb_req.transfer_buffer))

        if self.mode == MODE_NORMAL:
            self.handle_out_normal_mode(usb_req)
        elif self.mode == MODE_Q:
            self.handle_out_q_mode(usb_req)
        elif self.mode == MODE_UNKNOWN:
            self.handle_out_unknown_mode(usb_req)
        else:
            raise ValueError(f"Invalid mode {self.mode}")
