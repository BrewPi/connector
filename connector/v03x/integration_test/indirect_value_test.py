from hamcrest import assert_that, greater_than_or_equal_to, is_, calling, raises, equal_to
from nose.plugins.attrib import attr
from connector.v03x.integration_test.base_test import BaseControllerTestHelper, ObjectTestHelper
from connector.v03x.objects import IndirectValue, PersistentValue
from connector.v03x.time import CurrentTicks

__author__ = 'mat'


@attr(fixture='v03x')
class IndirectValueTest(ObjectTestHelper):

    def test_can_read_readonly(self):
        holder = self.c.create_dynamic_container()
        ticks = self.c.create_object(CurrentTicks, container=holder)
        value = self.c.create_object(IndirectValue, ticks, container=holder)
        current_ticks = ticks.read()
        current_value = value.read()
        assert_that(current_value, is_(
            greater_than_or_equal_to(current_ticks)))
        self.c.current_profile.delete()

    def test_attempt_write_on_readonly(self):
        holder = self.c.create_dynamic_container()
        ticks = self.c.create_object(CurrentTicks, container=holder)
        value = self.c.create_object(IndirectValue, ticks, container=holder)
        assert_that(calling(value.write).with_args(
            1234), raises(AttributeError))

    def test_can_write(self):
        holder = self.c.create_dynamic_container()
        target = self.c.create_object(PersistentValue, b'A', container=holder)
        value = self.c.create_object(IndirectValue, target, container=holder)
        value.write(b'B')
        written = target.read()
        assert_that(written, is_(equal_to(b'B')))
