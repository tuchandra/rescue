"""
rescue_tests.py

Tests for rescue.py -- just the RNG for now.
"""

import unittest

from rescue import DotNetRNG, RescueCode, Symbol


class TestRNG(unittest.TestCase):
    """
    Test cases for the DotNetRNG class. Assert that we produce the right
    values for some seeds for which we were able to find examples online:

    https://docs.microsoft.com/en-us/dotnet/api/system.random.-ctor?view=netframework-4.8#System_Random__ctor_System_Int32_

    I also installed the .NET Core from

    https://docs.microsoft.com/en-us/dotnet/core/install/   linux-package-manager-ubuntu-1910

    and created test programs to validate results another way.
    """

    def test_seed_123(self):
        """Test that the RNG produces the right values for seed 123"""

        rng = DotNetRNG(123)
        assert rng.next() == 2114319875
        assert rng.next() == 1949518561
        assert rng.next() == 1596751841
        assert rng.next() == 1742987178
        assert rng.next() == 1586516133
        assert rng.next() == 103755708

    def test_seed_456(self):
        """Test that the RNG produces the right values for seed 456"""

        rng = DotNetRNG(456)
        assert rng.next() == 2044805024
        assert rng.next() == 1323311594
        assert rng.next() == 1087799997
        assert rng.next() == 1907260840
        assert rng.next() == 179380355
        assert rng.next() == 120870348

    def test_seed_12(self):
        """Test that the RNG produces the right values for seed 12"""

        rng = DotNetRNG(12)
        assert rng.next() == 2137491492
        assert rng.next() == 726598452
        assert rng.next() == 334746691
        assert rng.next() == 256573526
        assert rng.next() == 1339733510
        assert rng.next() == 98050828
        assert rng.next() == 607109598
        assert rng.next() == 992976482
        assert rng.next() == 992459907
        assert rng.next() == 1500484683


class TestSymbol(unittest.TestCase):
    """Test methods of Symbol"""

    def test_alphabet(self):
        assert len(Symbol.ALPHABET) == 64

    def test_text(self):
        assert Symbol("1f").text == "1f"
        assert Symbol("6h").text == "6h"
        assert Symbol("Xe").text == "Xe"
        assert Symbol("4w").text == "4w"
        assert Symbol("Pf").text == "Pf"

    def test_pos(self):
        assert Symbol("1f").pos == 0
        assert Symbol("5w").pos == 30

    def test_prev(self):
        assert Symbol("1f").prev == Symbol("Ds")  # wrapping
        assert Symbol("2w").prev == Symbol("1w")
        assert Symbol("Ph").prev == Symbol("9h")
        assert Symbol("1h").prev == Symbol("Xf")
        assert Symbol("Me").prev == Symbol("Pe")
        assert Symbol("8h").prev == Symbol("7h")

    def test_next(self):
        assert Symbol("1f").next == Symbol("2f")
        assert Symbol("2w").next == Symbol("3w")
        assert Symbol("9h").next == Symbol("Ph")
        assert Symbol("Ph").next == Symbol("Mh")
        assert Symbol("De").next == Symbol("Xe")
        assert Symbol("Xe").next == Symbol("1s")
        assert Symbol("Ds").next == Symbol("1f")  # wrapping


class TestRescueCode(unittest.TestCase):
    """Test methods of RescueCode"""

    basic_code = "Pf8sPs4fPhXe3f7h1h2h5s8w3h9s3fXh4wMw4s6w8w9w6e2f8h9f1h2s1w8h"

    def test_unshuffle(self):
        """Test that the unshuffle method puts symbols in the right spot

        Taken straight from:

        https://gist.github.com/zaksabeast/fed5730156e26fb3e805e234fcbea60b#unshuffling

        and copy/pasted to avoid transcription errors, hence the hex indexes.
        """

        code = RescueCode.from_text(TestRescueCode.basic_code)
        new_code = code.unshuffle()

        assert code.symbols[0] == new_code.symbols[3]
        assert code.symbols[1] == new_code.symbols[0x1B]
        assert code.symbols[2] == new_code.symbols[0xD]
        assert code.symbols[3] == new_code.symbols[0x15]
        assert code.symbols[4] == new_code.symbols[0xC]
        assert code.symbols[5] == new_code.symbols[9]
        assert code.symbols[6] == new_code.symbols[7]
        assert code.symbols[7] == new_code.symbols[4]
        assert code.symbols[8] == new_code.symbols[6]
        assert code.symbols[9] == new_code.symbols[0x11]
        assert code.symbols[10] == new_code.symbols[0x13]
        assert code.symbols[0xB] == new_code.symbols[0x10]
        assert code.symbols[0xC] == new_code.symbols[0x1C]
        assert code.symbols[0xD] == new_code.symbols[0x1D]
        assert code.symbols[0xE] == new_code.symbols[0x17]
        assert code.symbols[0xF] == new_code.symbols[0x14]
        assert code.symbols[0x10] == new_code.symbols[0xB]
        assert code.symbols[0x11] == new_code.symbols[0]
        assert code.symbols[0x12] == new_code.symbols[1]
        assert code.symbols[0x13] == new_code.symbols[0x16]
        assert code.symbols[0x14] == new_code.symbols[0x18]
        assert code.symbols[0x15] == new_code.symbols[0xE]
        assert code.symbols[0x16] == new_code.symbols[8]
        assert code.symbols[0x17] == new_code.symbols[2]
        assert code.symbols[0x18] == new_code.symbols[0xF]
        assert code.symbols[0x19] == new_code.symbols[0x19]
        assert code.symbols[0x1A] == new_code.symbols[10]
        assert code.symbols[0x1B] == new_code.symbols[5]
        assert code.symbols[0x1C] == new_code.symbols[0x12]
        assert code.symbols[0x1D] == new_code.symbols[0x1A]

    def test_to_bitstream(self):
        """Test the to_bitstream method"""

        code = RescueCode.from_text(TestRescueCode.basic_code)
        bits = code.to_bitstream()

        assert len(bits) == 180

        # Paired tests - that the first symbol is indeed the one for a 9,
        # then that the bitstring has a binary 9 as the first 6 chars
        assert code.to_numbers()[0] == 9  # Pf
        assert bits[:6] == "001001"

        assert code.to_numbers()[1] == 59  # 8s
        assert bits[6:12] == "111011"

        assert code.to_numbers()[5] == 51  # Xe
        assert bits[30:36] == "110011"


if __name__ == "__main__":
    unittest.main()

