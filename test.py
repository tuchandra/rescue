"""
rescue_tests.py

Tests for rescue.py -- just the RNG for now.
"""

import unittest

from rescue import DotNetRNG


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


if __name__ == "__main__":
    unittest.main()

