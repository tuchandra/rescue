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


if __name__ == "__main__":
    unittest.main()

