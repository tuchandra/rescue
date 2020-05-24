"""
rescue.py

Utilities for encoding and decoding rescue passwords.

"""

from __future__ import annotations

import json
import string
import textwrap
import time

from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from pyodide import open_url

# This is the equivalent of
#  with open("gamedata.json") as f: romdata = json.load(f)
# where we have to use open_url because we plan to run this in-browser.
romdata = json.loads(open_url("python/gamedata.json").read())

# These are maps from dungeon_name : index, pokemon_species : index, etc., where the
# indexes are what get encoded into passwords
valid_dungeons = {
    info["name"]: index
    for index, info in enumerate(romdata["dungeons"])
    if info["valid"]
}
valid_pokemon = {
    info["name"]: index
    for index, info in enumerate(romdata["pokemon"])
    if info["valid"]
}
valid_genders = {
    info["name"]: index
    for index, info in enumerate(romdata["genders"])
    if info["valid"]
}
valid_rewards = {
    info["name"]: index
    for index, info in enumerate(romdata["rewards"])
    if info["valid"]
}

Password = List[int]


def get_romdata_entry(table: str, index: int):
    """Get entry stored at an index within a particular (global) romdata table"""

    if index >= len(romdata[table]):
        if table == "dungeons":
            return {
                "ascending": False,
                "const": "",
                "floors": 0,
                "name": "",
                "valid": False,
            }
        return {"const": "", "name": "", "valid": False}
    return romdata[table][index]


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


def apply_shuffle(code: Password, reverse=False) -> Password:
    """Apply shuffle (for decrypting) or unshuffle (for encrypting) to array elements"""

    shuffle = [
        # fmt:off
        3, 27, 13, 21, 12, 9, 7, 4, 6, 17, 19, 16, 28, 29, 23,
        20, 11, 0, 1, 22, 24, 14, 8, 2, 15, 25, 10, 5, 18, 26,
        # fmt: on
    ]
    newcode: List[int] = [-1] * len(shuffle)
    for i, x in enumerate(shuffle):
        if not reverse:
            newcode[i] = code[x]
        else:
            newcode[x] = code[i]

    return newcode


def apply_bitpack(code: Password, origbits: int, destbits: int) -> Password:
    """
    Given array `code` of `origbits`-sized items, reinterpret as array of
    `destbits`-sized items by packing into bitstream then unpacking in new size.
    """

    newcode = []
    reader = BitstreamReader(code, origbits)
    while reader.remaining():
        newcode.append(reader.read(destbits))
    return newcode


def apply_crypto(code: Password, encrypt: bool = False) -> Password:
    """
    Encode / decode a password using the PRNG "crypto".
    """

    newcode = [code[0], code[1]]
    rng = DotNetRNG(code[0] | code[1] << 8)
    for x in code[2:]:
        val = rng.next()
        if encrypt:
            val = -val
        newcode.append((x - val) & 0xFF)

    # Ignore the part that's 0 as a result of bitpacking
    remain = 8 - (len(code) * 8 % 6)
    newcode[len(newcode) - 1] &= (1 << remain) - 1
    return newcode


def checksum(code: Password) -> int:
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
        sum = romdata["crc32table"][(sum & 0xFF) ^ x] ^ (sum >> 8)
    return sum ^ 0xFFFFFFFF


def get_team_name(team: List[int]) -> str:
    """Decode list of ints to readable team name using romdata"""

    team_name = ""
    for char in team:
        if char == 0:
            break
        if char < 402:
            team_name += romdata["charmap_text"][char]
        else:
            team_name += "*"

    return team_name


def get_team_numbers(name: str) -> List[int]:
    """Encode up-to-11-char team name into a list of ints using romdata"""

    charmap = romdata["charmap_text"]

    team_numbers = []
    for char in name:
        if char in charmap:
            team_numbers.append(charmap.index(char))
        else:
            raise ValueError("Encoding team name {name} failed")

    return team_numbers


@dataclass
class RescueCode:
    """
    Pieces of a rescue code.

    Details
    -------
    Both rescue and revival passwords have:
     - timestamp (32 bit, unixtime)
     - type (0 for rescue, 1 for revival)
     - an unknown bit (always 0?)
     - team name (11 * 8 bits, padded at the end with 0s if needed)

    Only rescue passwords will have:
     - dungeon (7 bits)
     - floor (7)
     - last pokemon to faint (11)
     - gender (2)
     - reward (2)
     - another unknown bit

    All of these values are read off from a decoded rescue password (i.e., unshuffled, bitpacked,
    and passed through the PRNG crypto).

    Finally, rescue passwords will have a "revive" value that's computed as a crc32 hash
    of the *original* (not decoded) password.
    """

    timestamp: int
    team_name: List[int]
    dungeon: int
    floor: int
    pokemon: int
    gender: int
    reward: int

    # these are all computed from the above or unnecessary
    checksum: int = 0
    calculated_checksum: int = 0
    revive: int = 0
    unk1: int = 0
    unk2: int = 0
    type: int = 0  # this is always 0 for rescue codes

    @classmethod
    def from_password(cls, password: Password):
        """Get rescue code components from original & decoded passwords"""

        unshuffled = apply_shuffle(password)
        repacked = apply_bitpack(unshuffled, 6, 8)
        decoded = apply_crypto(repacked, encrypt=False)

        # now we just have to decode everything
        info: Dict[str, Any] = {}
        info["checksum"] = decoded[0]
        info["calculated_checksum"] = checksum(decoded[1:])

        reader = BitstreamReader(decoded[1:])
        info["timestamp"] = reader.read(32)
        info["type"] = reader.read(1)
        info["unk1"] = reader.read(1)

        team_name: List[int] = []
        for x in range(12):
            team_name.append(reader.read(9))
        info["team_name"] = team_name

        info["dungeon"] = reader.read(7)
        info["floor"] = reader.read(7)
        info["pokemon"] = reader.read(11)
        info["gender"] = reader.read(2)
        info["reward"] = reader.read(2)
        info["unk2"] = reader.read(1)

        # this is the only part that requires the original code
        charcode = ""
        for x in password:
            charcode += romdata["charmap"][x]
        info["revive"] = crc32(charcode.encode("utf8")) & 0x3FFFFFFF

        return cls(**info)

    @classmethod
    def from_scratch(
        cls,
        dungeon_name: str,
        floor: int,
        team_name: str = "tusharc.dev",
        pokemon: str = "Spheal",
        gender: str = "Male",
        reward: str = "Deluxe",
    ):
        """Generate rescue code from nothing"""

        # Get indices of all the different pieces
        info: Dict[str, Any] = {}

        try:
            info["dungeon"] = valid_dungeons[dungeon_name]
            info["pokemon"] = valid_pokemon[pokemon]
            info["gender"] = valid_genders[gender]
            info["reward"] = valid_rewards[reward]
        except KeyError:
            print("One of dungeon, pokemon, gender, or reward was invalid")
            raise

        info["floor"] = floor
        info["team_name"] = get_team_numbers(team_name)
        info["timestamp"] = int(datetime.now().timestamp())

        return cls(**info)

    def read_romdata(self, name: str, value: int) -> str:
        """Decode dungeon, pokemon, gender, or reward field using romdata"""

        romdata_entry = {
            # name: romdata entry
            "dungeon": get_romdata_entry("dungeons", value),
            "pokemon": get_romdata_entry("pokemon", value),
            "gender": get_romdata_entry("genders", value),
            "reward": get_romdata_entry("rewards", value),
        }[name]

        decoded_value = romdata_entry["name"]
        if not romdata_entry["valid"]:
            decoded_value += " (!)"

        return decoded_value

    def get_floor(self, floor: int) -> str:
        """Get floor text"""

        dungeon_data = get_romdata_entry("dungeons", self.dungeon)

        if not dungeon_data["ascending"]:
            floor_text = f"B{floor}"
        else:
            floor_text = f"{floor}"
        if floor == 0 or floor > dungeon_data["floors"]:
            floor_text += " (!)"

        return floor_text

    def to_text(self) -> str:
        """Convert to text - use lookup table to figure out what all the numbers mean"""

        dungeon = self.read_romdata("dungeon", self.dungeon)
        pokemon = self.read_romdata("pokemon", self.pokemon)
        gender = self.read_romdata("gender", self.gender)
        reward = self.read_romdata("reward", self.reward)
        floor = self.get_floor(self.floor)

        info_text = "\n".join(
            [
                f"Checksum: 0x{self.checksum:02X} (calculated: {self.calculated_checksum:02X})",
                f"Revive: 0x{self.revive:06X}",
                f"Timestamp: {datetime.utcfromtimestamp(self.timestamp)}",
                f"Team: {get_team_name(self.team_name)}",
                f"Dungeon: {dungeon} {floor}",
                f"Pokemon: {pokemon}",
                f"Gender: {gender}",
                f"Reward: {reward}",
            ]
        )

        return info_text

    def validate(self) -> bool:
        """Check if code is valid"""

        if self.checksum != self.calculated_checksum:
            return False

        # this line can cause an error if the code is *very* wrong, so compute the checksum
        # as a first pass for correctness
        return not "(!)" in self.to_text()


@dataclass
class RevivalCode:
    timestamp: int
    team_name: List[int]
    revive: int
    unk1: int = 0
    type: int = 1

    @classmethod
    def from_rescue_code(cls, rescue: RescueCode, team_name: str = None):
        """Create revival code from a rescue code"""

        timestamp = int(datetime.now().timestamp())
        unk1 = 1

        # We need a list of ints to pass to the class, not a string; note that
        # RescueCode already has the list of ints, but if a new name
        # is passed, we have to convert it
        if team_name is not None:
            team_numbers = get_team_numbers(team_name)
        else:
            team_numbers = rescue.team_name

        return cls(
            timestamp=timestamp,
            team_name=team_numbers,
            revive=rescue.revive,
            unk1=unk1,
        )


def rescue_password_from_text(text: str) -> Password:
    """Read a string of 60 uninterrupted characters and turn into symbol values"""

    if len(text) != 60:
        raise ValueError(
            "Length of text provided must be exactly 60 chars (30 symbols)"
        )

    text = text.upper()
    symbols = [text[i : i + 2] for i in range(0, 60, 2)]
    numbers = [get_index_of_symbol(s) for s in symbols]

    return numbers


def code_to_symbols(info: Union[RescueCode, RevivalCode]) -> List[str]:
    """Given a code, generate the symbols (1h Pe etc.) that comprise the code in-game."""

    writer = BitstreamWriter()
    writer.write(info.timestamp, 32)
    writer.write(info.type, 1)
    writer.write(info.unk1, 1)
    for x in range(12):
        if x < len(info.team_name):
            writer.write(info.team_name[x], 9)
        else:
            writer.write(0, 9)
    if isinstance(info, RescueCode):
        writer.write(info.dungeon, 7)
        writer.write(info.floor, 7)
        writer.write(info.pokemon, 11)
        writer.write(info.gender, 2)
        writer.write(info.reward, 2)
        writer.write(info.unk2, 1)
    else:
        writer.write(info.revive, 30)

    code = writer.finish()
    code = [checksum(code)] + code

    code = apply_crypto(code, encrypt=True)
    code = apply_bitpack(code, 8, 6)
    code = apply_shuffle(code, reverse=True)

    symbols = [get_symbol_from_index(i) for i in code]
    return symbols


if __name__ == "__main__":
    # i don't think this will ever work because of the open_url call at the top but whatever
    ex = "Pf8sPs4fPhXe3f7h1h2h5s8w3h9s3fXh4wMw4s6w8w9w6e2f8h9f1h2s1w8h"
    password = rescue_password_from_text(ex)
    rescue = RescueCode.from_password(password)
    revival = RevivalCode.from_rescue_code(rescue)
    print(revival)
