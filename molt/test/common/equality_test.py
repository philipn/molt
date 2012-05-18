# encoding: utf-8
#
# Copyright (C) 2011-2012 Chris Jerdonek. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * The names of the copyright holders may not be used to endorse or promote
#   products derived from this software without specific prior written
#   permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

"""
TODO: add a docstring.

"""

from __future__ import absolute_import

import unittest

from ...common.equality import Equalable


class Foo(Equalable):

    def __init__(self, bar):
        self.bar = bar


class Bar(Foo):

    pass


class EqualableTestCase(unittest.TestCase):

    def testSameObject(self):
        foo = Foo(1)
        self.assertTrue(foo == foo)
        self.assertFalse(foo != foo)

    def testEqualObjects(self):
        foo1, foo2 = Foo(1), Foo(1)
        self.assertTrue(foo1 == foo2)
        self.assertFalse(foo1 != foo2)

    def testUnequalObjects(self):
        foo1, foo2 = Foo(1), Foo(2)
        self.assertTrue(foo1 != foo2)
        self.assertFalse(foo1 == foo2)

    # Make sure None doesn't throw exceptions, for example.
    def testNone(self):
        foo = Foo(1)
        self.assertTrue(foo != None)
        self.assertTrue(None != foo)
        self.assertFalse(foo == None)
        self.assertFalse(None == foo)

    def testSubclass(self):
        foo, bar = Foo(1), Bar(1)
        self.assertTrue(foo != bar)
        self.assertTrue(bar != foo)
        self.assertFalse(foo == bar)
        self.assertFalse(bar == foo)

