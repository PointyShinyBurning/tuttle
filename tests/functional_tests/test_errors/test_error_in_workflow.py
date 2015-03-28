# -*- coding: utf-8 -*-

from tests.functional_tests import FunctionalTestBase, isolate

class TestErrorInWorkflow(FunctionalTestBase):

    @isolate
    def test_missing_primary_resource(self):
        """ Should fail if a primary resource is missing"""
        project = """file://B <- file://A
    echo A produces B
    echo B > B
"""
        self.write_tuttlefile(project)
        rcode, output = self.run_tuttle()
        assert rcode == 2
        assert output.find("Missing") >= 0, output

