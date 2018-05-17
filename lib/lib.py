import struct
from ctypes import *
import socket



class IP(Structure):
    _fields_ = [
        ("ihl", c_ubyte, 4),
        ("version", c_ubyte, 4),
        ("tos", c_ubyte),
        ("len", c_ushort),
        ("id", c_ushort),
        ("flags", c_ushort),
        ("ttl", c_ubyte),
        ("protocol_num", c_ubyte),
        ("sum", c_ushort),
        ("src", c_ulong),
        ("dst", c_ulong)
    ]

    def __new__(self, socket_buffer=None):
        return self.from_buffer_copy(socket_buffer)

    def __init__(self, socket_buffer=None):

        # map protocol constants to their names
        self.protocol_map = {6: "TCP", 17: "UDP", 1: "ICMP"}

        # human readable IP addresses
        self.src_address = socket.inet_ntoa(struct.pack("<L", self.src))
        self.dst_address = socket.inet_ntoa(struct.pack("<L", self.dst))

        self.ttl = self.ttl

        # human readable protocol
        try:
            self.protocol = self.protocol_map[self.protocol_num]
        except:
            self.protocol = str(self.protocol_num)


class ICMPv4(Structure):
    _fields_ = [
        ("icmp_type", c_ubyte),
        ("icmp_code", c_ubyte),
        ("checksum", c_ushort),
        ("id", c_ushort),
        ("sequence", c_ushort)
    ]

    def __new__(self, socket_buffer):
        return self.from_buffer_copy(socket_buffer)

    def __init__(self, socket_buffer):
        self.icmp_type = self.icmp_type
        self.icmp_code = self.icmp_code
        self.checksum = struct.unpack(">H", struct.pack("<H", self.checksum))[0]
        self.id_le = self.id
        self.id_be = struct.unpack(">H", struct.pack("<H", self.id))[0]
        self.sequence_le = self.sequence
        self.sequence_be = struct.unpack(">H", struct.pack("<H", self.sequence))[0]