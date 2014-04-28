from hamcrest import assert_that, greater_than_or_equal_to, is_, calling, raises, equal_to
from connector.v03x.integration_test.base_test import BaseControllerTestHelper
from connector.v03x.objects import IndirectValue, PersistentValue
from connector.v03x.time import CurrentTicks

__author__ = 'mat'

class IndirectValueTest(BaseControllerTestHelper):
    def test_can_read_readonly(self):
        p = self.setup_profile()
        ticks = self.c.create_object(CurrentTicks)
        value = self.c.create_object(IndirectValue, ticks)
        current_ticks = ticks.read()
        current_value = value.read()
        assert_that(current_ticks, is_(greater_than_or_equal_to(current_value)))
        p.delete()

    def test_attempt_write_on_readonly(self):
        p = self.setup_profile()
        ticks = self.c.create_object(CurrentTicks)
        value = self.c.create_object(IndirectValue, ticks)
        assert_that(calling(value.write).with_args(1234), raises(AttributeError))

    def test_can_write(self):
        p = self.setup_profile()
        target = self.c.create_object(PersistentValue, b'A')
        value = self.c.create_object(IndirectValue, target)
        value.write(b'B')
        written = target.read()
        assert_that(written, is_(equal_to(b'B')))
