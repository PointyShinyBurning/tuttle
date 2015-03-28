#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path
from tests.functional_tests import FunctionalTestBase, isolate


class TestInvalidateResource(FunctionalTestBase):

    @isolate(['A'])
    def test_remove_resource(self):
        """If a resource is removed from a tuttlefile, it should be invalidated"""
        first = """file://B <- file://A
    echo A produces B
    echo B > B

file://C <- file://B
    echo B produces C
    echo C > C

file://D <- file://A
    echo A produces D
    echo D > D
"""
        self.write_tuttlefile(first)
        rcode, output = self.run_tuttle()
        assert path.exists('B')
        assert path.exists('C')
        assert path.exists('D')
        second = """file://C <- file://A
    echo A produces C
    echo C > C

file://D <- file://A
    echo A produces D
    echo D > D
"""
        self.write_tuttlefile(second)
        rcode, output = self.run_tuttle()
        # TODO shouldn't it fail ?
        assert rcode == 0
        assert output.find("* file://B") >= 0
        assert output.find("* file://C") >= 0
        assert output.find("* file://D") == -1


    @isolate(['A', 'B'])
    def test_resource_should_be_created_by_tuttle(self):
        """If a resource is removed from a tuttlefile, it should be invalidated"""
        first = """file://B <- file://A
    echo A produces B
    echo B > B
"""
        self.write_tuttlefile(first)
        rcode, output = self.run_tuttle()
        assert rcode == 0
        assert output.find("* file://B") >= 0