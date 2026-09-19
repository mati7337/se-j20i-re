# All stuff related to the EMP protocol used to communicate with
# old sony ericsson phones using USB
from common import BaseStructure, BaseStructureData

class ProtocolError(Exception):
    """Generic EMP Protocol exception"""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

USB_VID = 0x0fce
USB_PID = 0xadde
USB_EP_IN  = 0x84
USB_EP_OUT = 0x03

# For some reason the chip in J20i/J20a Hazel schematics is called DB3370 even though
# all other sources say it has the DB3350 chipset.
# I have some docs about DB3370/DB3430 but can't find any other mention of DB3370/DB3430
CHIP_IDS = {
    0xf100: "DB3350", # DB3350 P2x is taken from linux sources

    # These are taken from the internet
    0xe900: "DB3210", # according to some logs from random forums
    0xe800: "DB3210", # according to linux

    0xe000: "DB3250", # linux

    0xd900: "DB3200", # forums
    0xd800: "DB3200", # linux

    0xc900: "DB3150", # forums
    0xc800: "DB3150", # linux

    0xc000: "DB3100", # linux

    0xb800: "DB3000", # linux

    0x9900: "DB2020", # forums
    0x8040: "DB2010", # forums (DB2010 Marita compact)
}
CHIP_NAMES = {name: chip_id for chip_id, name in CHIP_IDS.items()}

EMPPROTO_VER = 0x0401 # 4.1?

VAR_LEN_MSG_MAGIC = 0x63

# Gets sent after connecting to the PC
HELLO_RESP = b"z"
# Some other Sony Ericsson phones seem to respond with 0x5a - uppercase "Z"
# Other Ericsson phones seem to respond with completely other characters, like ">" or "2"
# See seftool's src/core/connection.c
# For now just the "z" should be enough

# === Commands ===

# NOTE: there's some endianness fuckery going on
# Some fields seem to be little endian and some big endian

VAR_LEN_MAGIC = 0x63

CMD_IDENT = b"?"
class RespIdent(BaseStructure):
    _byte_order_ = '>'
    _fields_ = [
        ('chip_id', 'H'),
        ('emp_protocol', 'H'),
        ('padding', 'I', 0xffffffff),
    ]

# TODO: reverse
CMD_K = b"K"
RESP_K = b'\xff\xff\xff\xff\xff\xff\xff'

CMD_READ_OTP = b"ICO0"
# TODO verify endianess
class RespReadOTP(BaseStructure):
    _byte_order_ = '>'
    _fields_ = [
        ('var_len_magic', 'B', VAR_LEN_MAGIC),
        ('length', 'B', 0x13),
        # TODO verify if locked and PAF fields are correct and reverse what they do
        ('locked_guess', 'H', 0x0001),
        ('cid', 'B'),
        ('paf_guess', 'H', 0x0001),
        ('imei', '14s', b"0"*14),
    ]

CMD_READ_EROM_COLOR = b"IC30"
EROM_COLOR_BLACK = 0x08 # ??? sefp2 and seftool recognizes it, a2uploader does not
EROM_COLOR_RED   = 0x04 # Retail product
EROM_COLOR_BROWN = 0x02 # Developer device
EROM_COLOR_BLUE  = 0x01 # Factory device
EROM_COLORS = {
    EROM_COLOR_BLACK: "BLACK",
    EROM_COLOR_RED:   "RED",
    EROM_COLOR_BROWN: "BROWN",
    EROM_COLOR_BLUE:  "BLUE",
}
class RespReadEromColor(BaseStructure):
    _byte_order_ = '<'
    _fields_ = [
        ('var_len_magic', 'B', VAR_LEN_MAGIC),
        ('length', 'B', 0x04),
        # sefp2 considers only the first byte as the color
        # a2uploader reads the whole 4 bytes as "phone state"
        ('color', 'I'),
    ]
#RESP_READ_EROM_RED = bytes.fromhex("630404000000")

# a2uploader seems to refer to it as flash cid?
CMD_READ_EROM_CID = b"IC40"
class RespReadEromCid(BaseStructure):
    _byte_order_ = '<'
    _fields_ = [
        ('var_len_magic', 'B', VAR_LEN_MAGIC),
        ('length', 'B', 0x04),
        # sefp2 reads first byte, a2uploader whole 4 bytes
        ('cid', 'I'),
    ]

CMD_READ_SEMCBOOT_VER = b"ICE0"
class RespReadSemcbootVer(BaseStructureData):
    _byte_order_ = '<'
    _fields_ = [
        ('var_len_magic', 'B', VAR_LEN_MAGIC),
        ('length', 'B', 0x04),
    ]
    _data_field_ = 'data'

# unita doesn't seem to matter?
CMD_READ_EROM_VAR = b"ICG1"
class CMDReadEromVar(BaseStructure):
    _byte_order_ = '<'
    _fields_ = [
        ('cmd', '4s', b"ICG1"),
        ('unita', 'B', 0x02),
        ('unitb', 'H', 0x1062),
    ]

class RespReadEromVar(BaseStructureData):
    _byte_order_ = '<'
    _fields_ = [
        ('unita', 'B'),
        ('unitb', 'H'),
        ('length', 'I'),
    ]
    _data_field_ = 'data'

# This switches to a different mode in which a loader is received
CMD_SWITCH_MODE_Q = b"Q"
#RESP_Q  = b'\xaa\xfb\xee\xee\x00\x01\x00\x05\x88\xeb'
#CMD_Q2 = b'\xaa\xfb\xee\xee\x00\x02\x00\x04\x00\xa8\x6c'
#         b'\xaa\xfb\xee\xee\x00\x02\x00\x04\x00\xa8l'
class QHeader(BaseStructure):
    _byte_order_ = '<'
    _fields_ = [
        ('magic', '5s', b"\xaa\xfb\xee\xee\x00"),
        ('length', 'H'), # NOTE: length - 1
        ('unknown', 'B'),
    ]

# TODO: move QHeader usage to QMessage
class QMessage(BaseStructureData):
    _byte_order_ = '<'
    _fields_ = [
        ('magic', '5s', b"\xaa\xfb\xee\xee\x00"),
        ('length', 'H'), # NOTE: length - 1
        ('unknown', 'B'),
    ]
    _data_field_ = 'data'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not "length" in kwargs:
            self.length = len(self.data) - 1

"""
MSG_Q_ACK = b"\x00\xa8\x6c"
RESP_Q_ACK = QHeader(length=len(MSG_Q_ACK) - 1, unknown=0x04).pack() + MSG_Q_ACK
"""

"""
MSG_Q_NACK = b"\x01\x89\x7c"
RESP_Q_NACK = QHeader(length=len(MSG_Q_NACK) - 1, unknown=0x04).pack() + MSG_Q_NACK
"""

RESP_Q_ACK  = QMessage(unknown=0x04, data=b"\x00\xa8\x6c").pack()
RESP_Q_NACK = QMessage(unknown=0x04, data=b"\x01\x89\x7c").pack()
