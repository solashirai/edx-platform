
import os
import unittest
from pavelib.utils.test.suites.bokchoy_suite import BokChoyTestSuite

REPO_DIR = os.getcwd()


class TestPaverBokChoy(unittest.TestCase):

    def test_default_bokchoy(self):
        request = BokChoyTestSuite('paver test_bokchoy')
        expected_command = ("SCREENSHOT_DIR='{repo_dir}/test_root/log' "
                                       "HAR_DIR='{repo_dir}/test_root/log/hars' "
                                       "SELENIUM_DRIVER_LOG_DIR='{repo_dir}/test_root/log' "
                                       "nosetests {repo_dir}/common/test/acceptance/tests "
                                       "--with-xunit "
                                       "--xunit-file={repo_dir}/reports/bok_choy/xunit.xml "
                                       "--verbosity=2 ".format(repo_dir=REPO_DIR))
        self.assertEqual(request.cmd, expected_command)

    def test_suite_request_bokchoy(self):
        request = BokChoyTestSuite('paver test_bokchoy')
        request.test_spec = "test_foo.py"
        expected_command = ("SCREENSHOT_DIR='{repo_dir}/test_root/log' "
                                       "HAR_DIR='{repo_dir}/test_root/log/hars' "
                                       "SELENIUM_DRIVER_LOG_DIR='{repo_dir}/test_root/log' "
                                       "nosetests {repo_dir}/common/test/acceptance/tests/test_foo.py "
                                       "--with-xunit "
                                       "--xunit-file={repo_dir}/reports/bok_choy/xunit.xml "
                                       "--verbosity=2 ".format(repo_dir=REPO_DIR))
        self.assertEqual(request.cmd, expected_command)

    def test_class_request_bokchoy(self):
        request = BokChoyTestSuite('paver test_bokchoy')
        request.test_spec = "test_foo.py:FooTest"
        expected_command = ("SCREENSHOT_DIR='{repo_dir}/test_root/log' "
                                       "HAR_DIR='{repo_dir}/test_root/log/hars' "
                                       "SELENIUM_DRIVER_LOG_DIR='{repo_dir}/test_root/log' nosetests "
                                       "{repo_dir}/common/test/acceptance/tests/test_foo.py:FooTest "
                                       "--with-xunit "
                                       "--xunit-file={repo_dir}/reports/bok_choy/xunit.xml "
                                       "--verbosity=2 ".format(repo_dir=REPO_DIR))
        self.assertEqual(request.cmd, expected_command)

    def test_case_request_bokchoy(self):
        request = BokChoyTestSuite('paver test_bokchoy')
        request.test_spec = "test_foo.py:FooTest.test_bar"
        expected_command = ("SCREENSHOT_DIR='{repo_dir}/test_root/log' "
                                       "HAR_DIR='{repo_dir}/test_root/log/hars' "
                                       "SELENIUM_DRIVER_LOG_DIR='{repo_dir}/test_root/log' nosetests "
                                       "{repo_dir}/common/test/acceptance/tests/test_foo.py:FooTest.test_bar "
                                       "--with-xunit "
                                       "--xunit-file={repo_dir}/reports/bok_choy/xunit.xml "
                                       "--verbosity=2 ".format(repo_dir=REPO_DIR))
        self.assertEqual(request.cmd, expected_command)

    # TODO: Test when bok_choy test file is in a subdir