import EMPProto
import sys

with open(sys.argv[1], "rb") as fl:
    data_raw = fl.read()

while data_raw:
    header = EMPProto.QHeader.from_bytes(data_raw)
    packet_end = header.size() + header.length + 1
    packet = data_raw[header.size():packet_end]

    print(header)
    print(packet.hex())

    data_raw = data_raw[packet_end:]
