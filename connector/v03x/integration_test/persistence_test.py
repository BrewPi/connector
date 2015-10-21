from hamcrest import assert_that, equal_to, is_
from connector.v03x.integration_test.base_test import BaseControllerTestHelper, ObjectTestHelper
from connector.v03x.objects import PersistChangeValue, PersistentValue, PersistentShortValue


class PersistentChangeValueTest(ObjectTestHelper):

    def test_persist_change_value(self):
        """
        Ensures that the persisted value
        """
        v = self.c.create_object(PersistChangeValue, (-300, 50))
        self.reset()
        assert_that(v.value, is_(equal_to(-300)),
                    "expected initial value to be -300")
        v.value = -400
        self.reset()
        assert_that(v.value, is_(equal_to(-400)), "expected updated value")
        v.value = -420
        assert_that(v.value, is_(equal_to(-420)), "expected updated value")
        self.reset()
        assert_that(v.value, is_(equal_to(-400)), "expected value to be -400 since this was the last value with "
                    "difference > than threshold of 50")


class PersistentValueTest(ObjectTestHelper):
    """ Tests the PersistentValue object type. """

    def test_createAndPersistValue(self):
        holder = self.c.create_dynamic_container()
        p = self.c.create_object(
            PersistentValue, b'\x05\x06\x07', container=holder)
        assert_that(p.value, is_(equal_to(b'\x05\x06\x07')))
        self.reset()
        assert_that(p.value, is_(equal_to(b'\x05\x06\x07')))
        p.value = b'\x01\x02\x03'
        self.reset()
        assert_that(p.value, is_(equal_to(b'\x01\x02\x03')))

    def test_partial_write(self):
        p = self.c.create_object(PersistentValue, b'\x05\x06\x07')
        p.write_mask(b'\x9a\xf0\xff', b'\xfa\x80\x88')
        assert_that(p.value, is_(equal_to(b'\x9f\x86\x8f')))

    def test_shortEncodingType(self):
        p = self.c.create_object(PersistentShortValue, -400)
        assert_that(p.value, is_(-400))
        self.reset()
        assert_that(p.value, is_(-400),
                    "value should be persisted from previous set")
