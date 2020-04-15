"""
rescue.py

Brute-force rescue requests to reverse engineer the rescue code generator.

"""

from __future__ import annotations

import string
import time

import requests_html

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

        self.MBIG = 0x7FFFFFFF
        self.MSEED = 0x9A4EC86
        self.MZ = 0

        # Initialize the seed array
        self.seed_array = [0] * 56
        num2 = self.MSEED - abs(seed)  # called mj in C# code
        self.seed_array[55] = num2

        num3 = 1  # called mk in C# code
        for i in range(1, 55):
            index = (21 * i) % 55
            self.seed_array[index] = num3
            num3 = num2 - num3
            if num3 < 0:
                num3 += self.MBIG
            num2 = self.seed_array[index]

        for _ in range(1, 5):
            for k in range(1, 56):
                self.seed_array[k] -= self.seed_array[1 + (k + 30) % 55]
                if self.seed_array[k] < 0:
                    self.seed_array[k] += self.MBIG

        # what?
        self._inext = 0
        self._inextp = 21
        seed = 1  # what??

    def _internal_sample(self) -> int:
        """Internal sampling function to advance RNG"""

        # this is not really Pythonic but mirrors the original better
        inext = self._inext
        inextp = self._inextp

        # assignment expressions! replaces ++inext lines in original code
        if (inext := inext + 1) >= 56:
            inext = 1

        if (inextp := inextp + 1) >= 56:
            inextp = 1

        num = self.seed_array[inext] - self.seed_array[inextp]
        if num < 0:
            num += self.MBIG

        self.seed_array[inext] = num
        self._inext = inext
        self._inextp = inextp
        return num

    def next(self) -> int:
        """Advance RNG to get another integer."""

        return self._internal_sample()

    def smth(self):
        ...


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
        + [f"{x}s" for x in ("P", "M", "D", "X")]
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
        self.text = self.first + self.second

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

        if self.pos == 0:
            print(f"Asked for prev, but I am {self} - wrapping back around to the end")
            return Symbol.ALPHABET[-1]

        return Symbol(Symbol.ALPHABET[self.pos - 1])

    @property
    def next(self):
        """Get the next symbol in the alphabet"""

        if self.pos == 64:
            print(
                f"Asked for next, but I am {self} - wrapping back around to the start"
            )
            return Symbol.ALPHABET[0]

        return Symbol(Symbol.ALPHABET[self.pos + 1])

    def __repr__(self):
        return f"Symbol({self.first}{self.second})"


class RescueCode:
    """
    Class for rescue code requests.
    """

    SCRAMBLE = {
        # shuffled_index: unshuffled_index
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

    def __init__(self, symbols: list[Symbol]):
        """

        """

        self.base_url = "http://136.144.185.148/pmdrtdx/decode?c="
        self.symbols = symbols
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

    def create_url(self) -> str:
        """Create the URL to hit the rescue code generator."""

        return self.base_url + self.code_text

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
        """Unshuffle code based on hardcoded scramble"""

        scrambler = RescueCode.SCRAMBLE
        new_symbols = [None] * 30
        for i, symbol in enumerate(self.symbols):
            new_symbols[scrambler[i]] = symbol

        return RescueCode(new_symbols)

    def to_numbers(self) -> List[int]:
        """Convert code to array of numbers 0 - 63"""

        alpha = Symbol.ALPHABET
        return [alpha.index(s.text) for s in self.symbols]

    def to_bitstream(self) -> str:
        """Convert code to bitstream of 6 * 30 = 180 bits

        Each symbol represents a number 0 - 63, aka a 6-bit character.
        Convert the list of 30 symbols to a 180 bit-length bitstring.

        e.g., [8, 63] => 001000 111110, which are then concatenated
        """

        numbers = self.to_numbers()
        bits = [format(n, "06b") for n in numbers]
        return "".join(bits)

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


def parse_response(r: requests_html.HTMLResponse) -> tuple[str, str]:
    """Parse HTML response from rescue code website"""

    # There is one div on the page: it has either a warning why it didn't work
    # or an AOK code (that we don't care about for now)
    warning_or_aok = r.html.find("div", first=True).text

    # The response we want is in a readonly textarea
    textarea = r.html.find("textarea[readonly='']", first=True)
    return warning_or_aok, textarea.full_text


def run_one(code: RescueCode):
    """Run one trial - send a rescue code to server, log response"""

    url = code.create_url()
    resp = session.get(url)
    worked, decoded = parse_response(resp)

    print(code, "\n")
    if "WARNING!" in worked:
        print(worked, "\n")
    print(decoded)
    print("---\n")


def run_two(code: RescueCode, index: int):
    """
    Run code with a symbol incremented & code with same symbol decremented.

    The goal of this is to tease out the effect of each symbol.
    """

    curr = code.symbols[index]

    print(f"Decrementing index {index}: {curr} -> {curr.prev}")
    run_one(code.dec_symbol(index))

    print(f"Incrementing index {index}: {curr} -> {curr.next}")
    run_one(code.inc_symbol(index))


def run_many(code: RescueCode):
    """
    Run multiple trials where each symbol in a code is incremented / decremented

    The goal of this is to automate calling run_two over and over
    """

    run_one(ex_code)

    for idx in range(30):
        run_two(ex_code, idx)
        time.sleep(4)


session = requests_html.HTMLSession()

ex = "Pf8sPs4fPhXe3f7h1h2h5s8w3h9s3fXh4wMw4s6w8w9w6e2f8h9f1h2s1w8h"
code = RescueCode.from_text(ex)
