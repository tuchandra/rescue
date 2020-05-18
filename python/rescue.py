"""
rescue.py

My attempt at cracking the PMD RT:DX rescue code generator.


Classes
-------
DotNetRNG
    Implementation of the .NET random number generator, which PMD RT:DX
    uses since it is a Unity game.

Symbol
    Data class for storing one symbol within a rescue code, like 1/fire or
    X/star.

RescueCode
    Class for all the logic associated with rescue codes / passwords (terms
    used interchangeably). Includes methods to read from a text representation,
    convert to a bitstring, and decrypt. Not all of it works yet.

"""

from __future__ import annotations

import string
import time

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import romdata


class DotNetRNG:
    """
    Implementation of the .NET random number generator. This is what the game uses
    to encrypt & decrypt rescue passwords.

    References:
     - https://referencesource.microsoft.com/#mscorlib/system/random.cs
     - https://forum.kirupa.com/t/as3-seeded-pseudo-random-number-generator/322651

    Test cases:
     - https://docs.microsoft.com/en-us/dotnet/api/system.random.-ctor?view=netframework-4.8#System_Random__ctor_System_Int32_
    """

    def __init__(self, seed: int):
        self.seed = seed
        self.state = [0] * 56

        new_seed = 0x9A4EC86 - abs(seed)  # yup that's a magic number
        self.state[55] = new_seed

        value = 1
        for i in range(1, 55):
            self.state[(21 * i) % 55] = value
            temp = new_seed - value
            new_seed = value

            if temp < 0:
                temp += 0x7FFFFFFF
            value = temp

        for _ in range(4):
            # This is the other difference: the source says this loop is 1 - 56, the reference
            # implementation that *works* says 0 - 56 ... not sure.
            for k in range(0, 56):
                self.state[k] -= self.state[1 + (k + 30) % 55]
                if self.state[k] < 0:
                    self.state[k] += 0x7FFFFFFF

        self.i1 = 0
        self.i2 = 31
        # Based on my sources, i2 should start at 21 ... but the reference
        # implementation of the password cracker uses 31, and I have no idea why.
        # I'm switching it here purely to make it work ...

    def next(self) -> int:
        self.i1 += 1
        self.i2 += 1
        if self.i1 >= 56:
            self.i1 = 1
        if self.i2 >= 56:
            self.i2 = 1

        num = self.state[self.i1] - self.state[self.i2]
        if num < 0:
            num += 0x7FFFFFFF
        self.state[self.i1] = num

        return num


SYMBOL_ALPHABET = (
    [f"{i}F" for i in range(1, 10)]
    + [f"{x}F" for x in ("P", "M", "D", "X")]
    + [f"{i}H" for i in range(1, 10)]
    + [f"{x}H" for x in ("P", "M", "D", "X")]
    + [f"{i}W" for i in range(1, 10)]
    + [f"{x}W" for x in ("P", "M", "D", "X")]
    + [f"{i}E" for i in range(1, 10)]
    + [f"{x}E" for x in ("P", "M", "D", "X")]
    + [f"{i}S" for i in range(1, 10)]
    + [f"{x}S" for x in ("P", "M", "D")]
    # Note: Xs is never used!
)


def get_index_of_symbol(symbol: str):
    """
    Get the index that a rescue symbol (3-heart, 1-star, etc.) represents, from 0 - 63.

    `symbol` should be a two character string, case insensitive:
     - first character is any of 1 - 9, P, M, D, X
     - second character is f (fire), h (heart), w (water), e (emerald), s (star)
    """

    return SYMBOL_ALPHABET.index(symbol.upper())


def get_symbol_from_index(i: int):
    """Get the symbol at index i; silly function."""

    return SYMBOL_ALPHABET[i]


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

        ret = self.value & ((1 << count) - 1)
        self.value >>= count
        self.bits -= count
        return ret


@dataclass()
class BitstreamWriter:
    """
    Little-endian bitstream writer. This is the opposite of `BitstreamReader` and it's been
    too long since I stepped through the source code myself, so I don't have much info on this.

    This is also a dataclass purely for the sake of having a nice __repr__ (and being able
    to cut down on LOC).

    """

    bytesize: int = 8

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


def apply_bitpack(code: List[int], origbits: int, destbits: int) -> List[int]:
    """
    Given array `code` of `origbits`-sized items, reinterpret as array of
    `destbits`-sized items by packing into bitstream then unpacking in new size.
    """

    newcode = []
    reader = BitstreamReader(code, origbits)
    while reader.remaining():
        newcode.append(reader.read(destbits))
    return newcode


def apply_crypto(code: List[int], encrypt: bool = False) -> List[int]:
    """
    Encode / decode a password using the PRNG "crypto".
    """

    newcode = [code[0], code[1]]
    rng = DotNetRNG(code[0] | code[1] << 8)
    print(f"seed: {code[0] | code[1] << 8}")
    for x in code[2:]:
        val = rng.next()
        if encrypt:
            val = -val
        newcode.append((x - val) & 0xFF)
        print(f"rng: x={x}, val={val}, results in {(x - val) & 0xFF}")

    # Ignore the part that's 0 as a result of bitpacking
    remain = 8 - (len(code) * 8 % 6)
    newcode[len(newcode) - 1] &= (1 << remain) - 1
    return newcode


def checksum(code: List[int]) -> int:
    """Calculate checksum for code validation"""

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
    """What is this? Some kind of validation check?"""

    sum = 0xFFFFFFFF
    for x in bytes:
        sum = romdata.crc32table[(sum & 0xFF) ^ x] ^ (sum >> 8)
    return sum ^ 0xFFFFFFFF


def get_code_components(origcode: List[int], decoded_code: List[int]) -> Dict[str, Any]:
    """
    From the original code and decoded (post-shuffle/bitpack/crypto) code, read off the
    pieces of the code (e.g., dungeon, floor, etc.).

    Details
    -------
    Both rescue and revival passwords have:
     - timestamp (32 bit, unixtime)
     - type (0 for rescue, 1 for revival)
     - an unknown bit (always 0?)
     - team name (11 * 8 bits, padded at the end with 0s if needed)

    Rescue passwords will additionally have:
     - dungeon (7 bits)
     - floor (7)
     - last pokemon to faint (11)
     - gender (2)
     - reward (2)
     - another unknown bit

    The rescue passwords will have a "revive" value that's computed as a crc32 hash
    of the *original* password. Revival passwords, meanwhile, have this "revive"
    value encoded in the password directly.
    """

    info = {}
    info["code_checksum"] = decoded_code[0]
    info["calculated_checksum"] = checksum(decoded_code[1:])

    reader = BitstreamReader(decoded_code[1:])
    info["timestamp"] = reader.read(32)
    info["type"] = reader.read(1)
    info["unk1"] = reader.read(1)

    team_name = []
    for x in range(12):
        team_name.append(reader.read(9))
    info["team_name"] = team_name

    if info["type"] == 0:  # rescue password
        info["dungeon"] = reader.read(7)
        info["floor"] = reader.read(7)
        info["pokemon"] = reader.read(11)
        info["gender"] = reader.read(2)
        info["reward"] = reader.read(2)
        info["unk2"] = reader.read(1)

        # this is the only part that requires the original code
        charcode = ""
        for x in origcode:
            charcode += romdata.charmap[x]
        info["revive"] = crc32(charcode.encode("utf8")) & 0x3FFFFFFF
    else:  # revival password
        info["revive"] = reader.read(30)

    return info


def encode_code_components(info: Dict[str, Any], keep_checksum: bool = False):
    """
    Given code info (e.g., dungeon, floor, etc.), generate a rescue or revival code.
    """

    writer = BitstreamWriter()
    writer.write(info["timestamp"], 32)
    writer.write(info["type"], 1)
    writer.write(info["unk1"], 1)
    for x in range(12):
        if x < len(info["team_name"]):
            writer.write(info["team_name"][x], 9)
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


class RescueCode:
    """
    Rescue code / password object without all the baggage from last time.
    """

    SCRAMBLE = {
        # unshuffled index : shuffled index
        0: 3,
        1: 27,
        2: 13,
        3: 21,
        4: 12,
        5: 9,
        6: 7,
        7: 4,
        8: 6,
        9: 17,
        10: 19,
        11: 16,
        12: 28,
        13: 29,
        14: 23,
        15: 20,
        16: 11,
        17: 0,
        18: 1,
        19: 22,
        20: 24,
        21: 14,
        22: 8,
        23: 2,
        24: 15,
        25: 25,
        26: 10,
        27: 5,
        28: 18,
        29: 26,
    }

    def __init__(self, text: str):
        """Create rescue code from text string of 60 uninterrupted characters"""

        if len(text) != 60:
            raise ValueError(
                "Length of text provided must be exactly 60 chars (30 symbols)"
            )

        text = text.upper()
        self.symbols = [text[i : i + 2] for i in range(0, 60, 2)]
        self.numbers = [get_index_of_symbol(s) for s in self.symbols]

    def __repr__(self):
        return f"NEW RESCUE CODE \n" f"{self.symbols}\n" f"{self.numbers}"

    def shuffle(self, reverse=False) -> RescueCode:
        """Shuffle (or unshuffle) symbols into another instance of this class"""

        if reverse:
            scrambler = {v: k for k, v in RescueCode.SCRAMBLE.items()}
        else:
            scrambler = RescueCode.SCRAMBLE.items()

        new_symbols = self.symbols[:]
        for i, symbol in enumerate(self.symbols):
            new_symbols[scrambler[i]] = symbol

        return RescueCode("".join(new_symbols))

    def decode(self) -> Dict[str, Any]:
        """Decode code into dictionary of attributes (dungeon, floor, team, etc.)"""

        unshuffled_code = apply_shuffle(self.numbers)
        repacked_code = apply_bitpack(unshuffled_code, 6, 8)
        decoded_code = apply_crypto(repacked_code, encrypt=False)
        print(decoded_code)

        info = get_code_components(self.numbers, decoded_code)
        print(info)

        # Create revival password
        revival_info = dict(**info)
        revival_info["type"] = 1
        revival = encode_code_components(revival_info)
        revival_symbols = [get_symbol_from_index(i) for i in revival]
        print(revival)
        print(revival_symbols)


if __name__ == "__main__":
    ex = "Pf8sPs4fPhXe3f7h1h2h5s8w3h9s3fXh4wMw4s6w8w9w6e2f8h9f1h2s1w8h"
    code = RescueCode(ex)
    info = code.decode()
