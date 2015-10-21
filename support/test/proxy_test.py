from support.proxy import Proxy, make_delegation_class

__author__ = 'mat'

import unittest


class TestTarget:

    def __init__(self):
        self.a = 10

    def someFunc(self, offset):
        return 42 + offset

    def delegateFunc(self, offset):
        return self.someFunc(offset)

    def setA(self, v):
        self.a = v

    def getA(self):
        return self.a


class MyTestCase(unittest.TestCase):

    @unittest.skip("wip")
    def test_simpleProxyDoesNotChangeResult(self):
        p = Proxy(TestTarget())
        self.assertEqual(p.someFunc(0), 42)
        self.assertEqual(p.delegateFunc(10), 52)
        self.assertEqual(p.a, 10)

    @unittest.skip("wip")
    def test_proxyOverrideDelegateMethod(self):
        class OverrideDelegateProxy(Proxy):

            def someFunc(self, offset):
                return self.a + offset

        p = OverrideDelegateProxy(TestTarget())
        # a=10, offset 0, result is 10
        self.assertEqual(p.someFunc(0), 10)
        p.a = 20
        # a=20, offset 15, result is 35
        self.assertEqual(p.someFunc(15), 35)
        # self.assertEqual(p.delegateFunc(15), 35)    # direct call - if it's
        # 57, that means the original method is called, and not the proxy

    def test_makeProxy(self):
        TestTargetProxy = make_delegation_class(TestTarget)

        class OverrideDelegate(TestTargetProxy):

            def __init__(self):
                TestTargetProxy.__init__(self)

            def someFunc(self, offset):
                return self.getA() + offset

        p = OverrideDelegate()
        p.delegate_TestTarget(TestTarget())
        # a=10, offset 0, result is 10
        self.assertEqual(p.someFunc(0), 10)
        p.setA(20)
        # a=20, offset 15, result is 35
        self.assertEqual(p.someFunc(15), 35)
        # self.assertEqual(p.delegateFunc(15), 35)    # direct call - if it's
        # 57, that means the original method is called, and not the proxy


if __name__ == '__main__':
    unittest.main()
