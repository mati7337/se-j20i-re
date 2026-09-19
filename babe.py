from common import BaseStructure
import argparse
import os

# Info from https://github.com/farid1991/seftool
"""
# seftool - src/emp/v3/babe.h
struct babehdr_t {
	uint16_t sig; // 0xBEBA
	uint8_t unk; //
	uint8_t ver; // 03/04
	uint32_t color; // 00 - red, 0x60 - brown
	uint32_t platform; //
	uint32_t z1; // used by bootrom
	uint32_t cid; //
	uint32_t clr; // ???????? = 0xC1
	uint32_t f0[9]; // ffffffff
	uint8_t certplace[488]; //
	uint32_t prologuestart; //
	uint32_t prologuesize1; //
	uint32_t prologuesize2; //
	uint32_t unk1[4]; // 0,1,1,0xFFFFFFFF
	uint8_t hash1[128]; //
	uint32_t flags; // 0x200 - main/fs/sfa/cert [2C0]
	uint32_t unk2[4]; //
	uint32_t clr2; // ???????? = 0xC1
	uint32_t f1[3]; // ffffffff
	uint32_t payloadstart; //
	uint32_t payloadsize1; // numblocks
	uint32_t payloadsize2; //
	uint32_t flags2; // 10 - sfa, 1 - main/fs/cert
	uint32_t unk4[3]; // 1,1,0xFFFFFFFF
	uint8_t hash2[128]; //
};
"""

class BabeHeader(BaseStructure):
    _byte_order_ = '<'
    _fields_ = [
        ('sig', 'H'),
        ('unk', 'B'),
        ('ver', 'B'),
        ('color', 'I'),
        ('platform', 'I'),
        ('z1', 'I'),
        ('cid', 'I'),
        ('clr', 'I'),
        ('f0', '9I'),
        ('certplace', '488s'),
        ('prologuestart', 'I'),
        ('prologuesize1', 'I'),
        ('prologuesize2', 'I'),
        ('unk1', '4I'),
        ('hash1', '128s'),
        ('flags', 'I'),
        ('unk2', '4I'),
        ('clr2', 'I'),
        ('f1', '3I'),
        ('payloadstart', 'I'),
        ('payloadsize1', 'I'),
        ('payloadsize2', 'I'),
        ('flags2', 'I'),
        ('unk4', '3I'),
        ('hash2', '128s'),
    ]

def load_babe(babe_file):
    babe_header = BabeHeader.from_bytes(
        babe_file.read(BabeHeader.size())
    )

    # TODO data

    return babe_header

def load_babe_file(babe_path):
    if not os.path.exists(babe_path):
        raise ValueError(f"{args.input} doesn't exist")

    if not os.path.isfile(babe_path):
        raise ValueError(f"{args.input} is not a file")

    with open(babe_path, "rb") as babe_file:
        babe_header = load_babe(babe_file)

    if babe_header.sig != 0xbeba:
        raise Exception("Not a babe file")

    return babe_header

def print_babe_header(babe_header):
    #print(babe_header)
    #print()
    print(babe_header.str_multiline())
    #for i in babe_header

def babe_info(args):
    print(args.input)
    try:
        babe_header = load_babe_file(args.input)
    except Exception:
        print("Invalid babe file")
        return

    print_babe_header(babe_header)
    print()

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    info_parser = subparsers.add_parser("info", help="Show babe file info")
    info_parser.add_argument("input", type=str)
    info_parser.set_defaults(func=babe_info)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
