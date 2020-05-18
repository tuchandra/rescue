#!/usr/bin/env python3

from sys import stderr, exit
from datetime import datetime
import romdata

from dataclasses import dataclass, field
from typing import List

import pysnooper


class NumberGenerator:
    def __init__(self, seed):
        # Algorithm is accurate for seeds up to 16 bits in size
        seed = 0x9A4EC86 - seed
        self.state = [None] * 56
        self.state[0] = 0
        self.state[55] = seed

        self.i1 = 0
        self.i2 = 31

        value = 1
        for x in range(1, 55):
            self.state[(x * 21) % 55] = value
            temp = seed - value
            seed = value
            value = ((temp >> 31) & 0x7FFFFFFF) + temp

        for x in range(4):
            for x in range(56):
                index = (((x + 30) & 0xFF) % 55) + 1
                temp = self.state[x] - self.state[index]
                self.state[x] = ((temp >> 31) & 0x7FFFFFFF) + temp

    def get(self):
        self.i1 += 1
        self.i2 += 1
        if self.i1 > 55:
            self.i1 = 1
        if self.i2 > 55:
            self.i2 = 1
        result = self.state[self.i1] - self.state[self.i2]
        if result < 0:
            result += 0x7FFFFFFF
        self.state[self.i1] = result
        return result


@dataclass()
class BitstreamReader:
    """
    Little-endian bistream reader. Given an array `bytes` of size `bitesize`-bits,
    treat it as a bitstream and reinterpret it (through the `read` method) as
    `count`-sized bytes.

    This is a dataclass for the sake of having a nice __repr__.

    Example
    -------
    Let:
        bytes = [3, 53, 60, 34]
        bytesize = 6
        count = 8

    This means to reinterpret a size-6 byte array into size-8 bytes. To do this, we
    first read bytes as 6-bit integers:
        bytes => [0b000011, 0b110101, 0b111100, 0b100010]

    To get the first 8-bit chunk, we take all 6 bits of the first item (0b000011) and
    the lower 2 bits of the second item (0b01). Because it's little endian, this becomes
    (0b01 << 6) | 0b000011 = 0b01000011 = 0x43 = 67.

    That leaves us four bits from the second item (0b1101) plus the rest of the array.
    To get the second 8-bit chunk, the four bits remaining make up the lower four bits,
    and the upper four bits come from the lower four bits of the third item (0b1100).
    This becomes (0b1100 << 4) | 0b1101 = 0xCD = 205.

    We're left with two bits from the third item (0b11) and the entire fourth item
    (0b100010). As before, this becomes (0b100010 << 2) | 0b11 = 0x8b = 139.
    The output (successive calls to `self.read(8)`) is therefore [67, 205, 139].

    """

    bytes: List[int]
    bytesize: int = 8

    # do not use these when initializing the class
    pos: int = 0
    bits: int = 0
    value: int = 0

    def remaining(self):
        if self.pos < len(self.bytes):
            return True
        if self.bits > 0:
            return True
        return False

    def read(self, count):
        mask = (1 << self.bytesize) - 1
        while self.bits < count:
            if self.pos >= len(self.bytes):
                break
            self.value |= (self.bytes[self.pos] & mask) << self.bits
            self.bits += self.bytesize
            self.pos += 1
            print(self)

        ret = self.value & ((1 << count) - 1)
        self.value >>= count
        self.bits -= count
        print(self)
        return ret


@dataclass()
class BitstreamWriter:
    bytesize: int

    # do not use these when initializing the class
    bytes: List[int] = field(default_factory=list)
    bits: int = 0
    value: int = 0

    def finish(self):
        if self.bits > 0:
            self.bytes.append(self.value & ((1 << self.bytesize) - 1))
        return self.bytes

    def write(self, value, bits):
        self.value |= (value & ((1 << bits) - 1)) << self.bits
        self.bits += bits
        while self.bits >= self.bytesize:
            self.bytes.append(self.value & ((1 << self.bytesize) - 1))
            self.value >>= self.bytesize
            self.bits -= self.bytesize


def apply_shuffle(code, reverse=False):
    # Shuffle the array around
    shuffle = [
        # fmt:off
        3, 27, 13, 21, 12, 9, 7, 4, 6, 17, 19, 16, 28, 29, 23,
        20, 11, 0, 1, 22, 24, 14, 8, 2, 15, 25, 10, 5, 18, 26,
        # fmt: on
    ]
    newcode = [None] * len(shuffle)
    for i, x in enumerate(shuffle):
        if not reverse:
            newcode[i] = code[x]
        else:
            newcode[x] = code[i]
    return newcode


def apply_bitpack(code, origbits, destbits):
    """
    Given array `code` of `origbits`-sized items, reinterpret as array of
    `destbits`-sized items by packing into bitstream then unpacking in new size.
    """

    newcode = []
    reader = BitstreamReader(code, origbits)
    while reader.remaining():
        newcode.append(reader.read(destbits))
    return newcode


def apply_crypto(code, encrypt=False):
    # Apply the "crypto"
    newcode = [code[0], code[1]]
    gen = NumberGenerator(code[0] | code[1] << 8)
    print(f"seed: {code[0] | code[1] << 8}")
    for x in code[2:]:
        val = gen.get()
        if encrypt:
            val = -val
        newcode.append((x - val) & 0xFF)
        print(f"rng: {x=}, {val=}, results in {(x - val) & 0xFF}")

    # Ignore the part that's 0 as a result of bitpacking
    remain = 8 - (len(code) * 8 % 6)
    newcode[len(newcode) - 1] &= (1 << remain) - 1
    return newcode


def checksum(code):
    # Calculate checksum
    calc = code[0]
    for x in range(1, (len(code) - 1) // 2 * 2, 2):
        calc += code[x] | (code[x + 1] << 8)
    if len(code) % 2 == 0:
        calc += code[len(code) - 1]

    calc = ((calc >> 16) & 0xFFFF) + (calc & 0xFFFF)
    calc += calc >> 16
    calc = ((calc >> 8) & 0xFF) + (calc & 0xFF)
    calc += calc >> 8
    calc &= 0xFF
    calc ^= 0xFF
    return calc


def crc32(bytes):
    sum = 0xFFFFFFFF
    for x in bytes:
        sum = romdata.crc32table[(sum & 0xFF) ^ x] ^ (sum >> 8)
    return sum ^ 0xFFFFFFFF


def decode(code):
    origcode = code
    code = apply_shuffle(code)
    with pysnooper.snoop(depth=3):
        code = apply_bitpack(code, 6, 8)
    code = apply_crypto(code)
    print(code)

    info = {}
    info["incl_checksum"] = code[0]
    info["calc_checksum"] = checksum(code[1:])

    breakpoint()

    reader = BitstreamReader(code[1:])
    info["timestamp"] = reader.read(32)
    info["type"] = reader.read(1)
    info["unk1"] = reader.read(1)
    team = []
    for x in range(12):
        team.append(reader.read(9))
    info["team"] = team
    if info["type"] == 0:
        info["dungeon"] = reader.read(7)
        info["floor"] = reader.read(7)
        info["pokemon"] = reader.read(11)
        info["gender"] = reader.read(2)
        info["reward"] = reader.read(2)
        info["unk2"] = reader.read(1)

        charcode = ""
        for x in origcode:
            charcode += romdata.charmap[x]
        info["revive"] = crc32(charcode.encode("utf8")) & 0x3FFFFFFF
        breakpoint()
    else:
        info["revive"] = reader.read(30)

    return info


def encode(info, keep_checksum=False):
    writer = BitstreamWriter()
    writer.write(info["timestamp"], 32)
    writer.write(info["type"], 1)
    writer.write(info["unk1"], 1)
    for x in range(12):
        if x < len(info["team"]):
            writer.write(info["team"][x], 9)
        else:
            writer.write(0, 9)
    if info["type"] == 0:
        writer.write(info["dungeon"], 7)
        writer.write(info["floor"], 7)
        writer.write(info["pokemon"], 11)
        writer.write(info["gender"], 2)
        writer.write(info["reward"], 2)
        writer.write(info["unk2"], 1)
    else:
        writer.write(info["revive"], 30)

    code = writer.finish()
    if keep_checksum:
        code = [info["incl_checksum"]] + code
    else:
        code = [checksum(code)] + code
    code = apply_crypto(code, encrypt=True)
    code = apply_bitpack(code, 8, 6)
    code = apply_shuffle(code, reverse=True)

    return code


def print_info(info):
    info_text = ""

    info_text += "Checksum: 0x%02X (calculated: 0x%02X)\n" % (
        info["incl_checksum"],
        info["calc_checksum"],
    )
    info_text += "Timestamp: %s\n" % datetime.utcfromtimestamp(info["timestamp"])
    info_text += "Revive: %s\n" % (info["type"] == 1)
    info_text += "Unk1: 0x%X\n" % info["unk1"]

    info_text += "Team Name: "
    for char in info["team"]:
        if char == 0:
            break
        if char < 402:
            info_text += romdata.charmap_text[char]
        else:
            info_text += "*"
    info_text += "\n"

    if info["type"] == 0:
        dungeon = romdata.get_index("dungeons", info["dungeon"])
        info_text += "Dungeon (%d): %s" % (info["dungeon"], dungeon["name"])
        if not dungeon["valid"]:
            info_text += " (!)"
        info_text += "\n"

        floor = "%dF" % info["floor"]
        if not dungeon["ascending"]:
            floor = "B" + floor
        info_text += "Floor: %s" % floor
        if info["floor"] == 0 or info["floor"] > dungeon["floors"]:
            info_text += " (!)"
        info_text += "\n"

        pokemon = romdata.get_index("pokemon", info["pokemon"])
        info_text += "Pokemon (%d): %s" % (info["pokemon"], pokemon["name"])
        if not pokemon["valid"]:
            info_text += " (!)"
        info_text += "\n"

        gender = romdata.get_index("genders", info["gender"])
        info_text += "Gender: %s" % gender["name"]
        if not gender["valid"]:
            info_text += " (!)"
        info_text += "\n"

        reward = romdata.get_index("rewards", info["reward"])
        info_text += "Reward: %s" % reward["name"]
        if not reward["valid"]:
            info_text += " (!)"
        info_text += "\n"

        info_text += "Unk2: 0x%X\n" % info["unk2"]

    info_text += "Revive value: 0x%08X\n" % info["revive"]
    return info_text


if __name__ == "__main__":
    # fmt:off
    charmap_symbols = [
        "1F", "2F", "3F", "4F", "5F", "6F", "7F", "8F", "9F", "PF", "MF", "DF", "XF",
        "1H", "2H", "3H", "4H", "5H", "6H", "7H", "8H", "9H", "PH", "MH", "DH", "XH",
        "1W", "2W", "3W", "4W", "5W", "6W", "7W", "8W", "9W", "PW", "MW", "DW", "XW",
        "1E", "2E", "3E", "4E", "5E", "6E", "7E", "8E", "9E", "PE", "ME", "DE", "XE",
        "1S", "2S", "3S", "4S", "5S", "6S", "7S", "8S", "9S", "PS", "MS", "DS", #"XS",
    ]
    # fmt:on

    import json

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--decode", action="store_true")
    parser.add_argument("-e", "--encode", action="store_true")
    parser.add_argument("-i", "--info", action="store_true")
    parser.add_argument("-k", "--keep-checksum", action="store_true")
    parser.add_argument("password")
    args = parser.parse_args()

    info = None

    if args.decode:
        code = "".join(args.password.split()).upper()
        if len(code) != 30 * 2:
            print("Invalid code length", file=stderr)
            exit(1)

        # Convert the characters to codepoints
        newcode = []
        for x in range(len(code) // 2):
            char = code[x * 2 : x * 2 + 2]
            newcode.append(charmap_symbols.index(char))
        code = newcode

        info = decode(code)
        print(json.dumps(info))

    if args.encode:
        if not info:
            info = json.loads(args.password)

        code = encode(info, keep_checksum=args.keep_checksum)
        i = 0
        for x in code:
            print(charmap_symbols[x], end="")
            i += 1
            if i % 15 == 0:
                print()
            elif i % 5 == 0:
                print(" ", end="")
        info = decode(code)

    if args.info and info:
        print(print_info(info))
