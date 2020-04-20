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

from dataclasses import dataclass
from typing import List, Tuple


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
            for k in range(1, 56):
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
        self.i2 += 2
        if self.i1 >= 56:
            self.i1 = 1
        if self.i2 >= 56:
            self.i2 = 1

        num = self.state[self.i1] - self.state[self.i2]
        if num < 0:
            num += 0x7FFFFFFF
        self.state[self.i1] = num

        return num



        self.seed_array[inext] = num
        self._inext = inext
        self._inextp = inextp
        return num

    def next(self) -> int:
        """Advance RNG to get another integer."""

        return self._internal_sample()


class Symbol:
    """
    Possible rescue character values, like 3-heart, 1-star, etc.

    Initialized via two-character string, case insensitive:
     - first character is any of 1 - 9, P, M, D, X
     - second character is f (fire), h (heart), w (water), e (emerald), s (star)
    """

    ALPHABET = (
        [f"{i}f" for i in range(1, 10)]
        + [f"{x}f" for x in ("P", "M", "D", "X")]
        + [f"{i}h" for i in range(1, 10)]
        + [f"{x}h" for x in ("P", "M", "D", "X")]
        + [f"{i}w" for i in range(1, 10)]
        + [f"{x}w" for x in ("P", "M", "D", "X")]
        + [f"{i}e" for i in range(1, 10)]
        + [f"{x}e" for x in ("P", "M", "D", "X")]
        + [f"{i}s" for i in range(1, 10)]
        + [f"{x}s" for x in ("P", "M", "D")]
        # Note: Xs is never used!
    )

    def __init__(self, text: str):
        first = text[0].upper()
        second = text[1].lower()

        if first not in (string.digits + "PMDX") and first != "0":
            raise ValueError("First char must be digit 1 - 9 or P, M, D, X")
        if second not in "fhwes":
            raise ValueError(
                "Second char must be f (fire), h (heart), w (water), e (emerald), s (star)"
            )

        self.first = first
        self.second = second

    @property
    def text(self):
        """Symbol text; Symbol(1f) => '1f'"""

        return self.first + self.second

    @property
    def pos(self):
        """
        The alphabet goes 1 - 9, P, M, D, X for fire, heart, water, emerald, star.

        1f = 0, 2f = 1, ... Xs = 64. Compute the position 0 - 64.
        """

        return Symbol.ALPHABET.index(self.text)

    @property
    def prev(self):
        """Get the previous symbol in the alphabet"""

        if self.text == "1f":
            print(f"Asked for prev, but I am {self} - wrapping back around to the end")
            return Symbol(Symbol.ALPHABET[-1])

        return Symbol(Symbol.ALPHABET[self.pos - 1])

    @property
    def next(self):
        """Get the next symbol in the alphabet"""

        if self.text == "Ds":
            print(
                f"Asked for next, but I am {self} - wrapping back around to the start"
            )
            return Symbol(Symbol.ALPHABET[0])

        return Symbol(Symbol.ALPHABET[self.pos + 1])

    def __repr__(self):
        return f"Symbol({self.first}{self.second})"

    def __eq__(self, other):
        if not isinstance(other, Symbol):
            return False

        return self.text == other.text


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


class RescueCode:
    """
    Class for rescue code requests.
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

    def __init__(self, symbols: List[Symbol]):
        """

        """

        self.symbols: List[Symbol] = symbols
        self.code_text = "".join(s.text for s in symbols)

    @classmethod
    def from_text(cls, text: str):
        """Create rescue code from text string of 60 uninterrupted characters"""

        if len(text) != 60:
            raise ValueError(
                "Length of text provided must be exactly 60 chars (30 symbols)"
            )

        symbols = [Symbol(text[i : i + 2]) for i in range(0, 60, 2)]
        return cls(symbols)

    def inc_symbol(self, index: int) -> RescueCode:
        """Return a RescueCode with one symbol incremented by one"""

        new = self.symbols[index].next
        new_symbols = self.symbols[:]  # to copy
        new_symbols[index] = new

        return RescueCode(new_symbols)

    def dec_symbol(self, index: int) -> RescueCode:
        """Return a RescueCode with one symbol deccremented by one"""

        new = self.symbols[index].prev
        new_symbols = self.symbols[:]  # to copy
        new_symbols[index] = new

        return RescueCode(new_symbols)

    def unshuffle(self) -> RescueCode:
        """Unshuffle (part of the decryption)"""

        scrambler = {v: k for k, v in RescueCode.SCRAMBLE.items()}
        new_symbols = self.symbols[:]
        for i, symbol in enumerate(self.symbols):
            new_symbols[scrambler[i]] = symbol

        return RescueCode(new_symbols)

    def shuffle(self) -> RescueCode:
        """Shuffle code (part of encryption)"""

        scrambler = RescueCode.SCRAMBLE
        new_symbols = self.symbols[:]
        for i, symbol in enumerate(self.symbols):
            new_symbols[scrambler[i]] = symbol

        return RescueCode(new_symbols)

    def to_numbers(self) -> List[int]:
        """Convert code to array of numbers 0 - 63"""

        alpha = Symbol.ALPHABET
        return [alpha.index(s.text) for s in self.symbols]

    def deserialize(self):
        """Full deserialization of password (mostly just decrypting)"""

        # Unshuffle first
        code = self.unshuffle()
        print(f"Unshuffled code: \n{code}")

        # Unpack into 8-bit bytes (see BitstreamReader for details, this is complex)
        reader = BitstreamReader(code.to_numbers(), 6)
        new_code = []
        while reader.remaining():
            new_code.append(reader.read(8))

        print(new_code)

        # Seed RNG with first two bytes
        seed = new_code[0] | (new_code[1] << 8)  # little endian
        print(f"{seed=}")
        rng = DotNetRNG(seed)

        # For each byte: advance RNG, subtract the random value from the byte,
        # take the lower 8 bits, write back to array
        for index in range(2, 23):
            random = rng.next()
            newvalue = new_code[index] - random
            print(f"{random=}, subtracted from {new_code[index]} gives {newvalue=}")
            new_code[index] = newvalue & 0xFF

        # For last byte, zero out the first four bits / just keep the bottom 4
        asbytes[22] = asbytes[22][4:]
        print(asbytes)

        # Calculate hash and validate (???)
        ...

        # Convert back into bitstream, starting at byte 1
        new_bitstream = "".join(asbytes[1:])
        print(f"{new_bitstream=}")

        return new_bitstream

    def __repr__(self):
        return (
            " ".join(c.text for c in self.symbols[:5])
            + " / "
            + " ".join(c.text for c in self.symbols[5:10])
            + " / "
            + " ".join(c.text for c in self.symbols[10:15])
            + "\n"
            + " ".join(c.text for c in self.symbols[15:20])
            + " / "
            + " ".join(c.text for c in self.symbols[20:25])
            + " / "
            + " ".join(c.text for c in self.symbols[25:30])
        )


if __name__ == "__main__":
    ex = "Pf8sPs4fPhXe3f7h1h2h5s8w3h9s3fXh4wMw4s6w8w9w6e2f8h9f1h2s1w8h"
    code = RescueCode.from_text(ex)
    info = code.deserialize()

