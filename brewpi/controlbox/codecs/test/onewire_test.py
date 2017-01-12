from unittest import TestCase

from brewpi.controlbox import OneWireAddress, OneWireCommandResult, OneWireBusRead


class OneWireAddressTest(TestCase):
    def test_decode_addresses_empty(self):
        self.assertEqual([], OneWireAddress.decode_addresses([]))

    def test_decode_addresses_single(self):
        self.assertEqual([OneWireAddress([1,2,3,4,5,6,7,8])], OneWireAddress.decode_addresses([1,2,3,4,5,6,7,8]))

    def test_decode_addresses_multiple(self):
        self.assertEqual([OneWireAddress([1,2,3,4,5,6,7,8]), OneWireAddress([11,12,13,14,15,16,17,18])],
                         OneWireAddress.decode_addresses([1,2,3,4,5,6,7,8,11,12,13,14,15,16,17,18]))


class OneWireBusTest(TestCase):
    def test_decode_fail(self):
        self.assertEqual(OneWireBusRead(success=False), OneWireCommandResult().decode(None, [-1]))

    def test_decode_success(self):
        self.assertEqual(OneWireBusRead(success=True), OneWireCommandResult().decode(None, [200]))

    def test_decode_success_addresses(self):
        self.assertEqual(OneWireBusRead(success=True, addresses=[
                OneWireAddress([1,2,3,4,5,6,7,8]),
                OneWireAddress([11,12,13,14,15,16,17,18])]),
                         OneWireCommandResult().decode(None, [0, 1,2,3,4,5,6,7,8, 11,12,13,14,15,16,17,18]))

