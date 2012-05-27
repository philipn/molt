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
Exposes make_template_tests() to check template directories.

"""

# TODO: unit test this module.

from __future__ import absolute_import

from filecmp import dircmp
import logging
import os
from pprint import pformat
from textwrap import dedent, TextWrapper
from unittest import TestCase

import molt
from molt.common import io
from molt.molter import Molter
from molt.test.harness.common import test_logger as _log
from molt.test.harness.common import indent, AssertFileMixin


TEST_FILE_ENCODING = 'utf-8'
DECODE_ERRORS = 'strict'

DIRCMP_ATTRS = ['left_only', 'right_only', 'funny_files']

# TODO: inject this value at run-time using load_tests().
SKIPPED_FILES = ['.DS_Store']


def make_expected_dir(template_dir):
    return os.path.join(template_dir, 'expected')


def make_template_test(group_name, template_dir):
    names = [None]

    def make_full_name(group_name, name):
        return group_name.lower()

    def make_assert_template(group_name, name, _template_dir):
        long_name = make_full_name(group_name, name)
        expected_dir = make_expected_dir(_template_dir)

        def assert_template(test_case):
            test_case._assert_template(group_name, long_name, _template_dir, expected_dir)

        return assert_template

    test_cases = _make_template_tests(group_name, names, template_dir, make_full_name, make_assert_template)

    return test_cases[0]


def make_template_tests(group_name, parent_input_dir):
    """
    Return a list of unittest.TestCase instances.

    """
    names = os.listdir(parent_input_dir)
    # Filter out '.DS_Store'.
    names = filter(lambda dir_name: not dir_name.startswith('.'), names)

    def make_full_name(group_name, name):
        return '%s__%s' % (group_name.lower(), name)

    def make_assert_template(group_name, name, parent_input_dir):
        template_dir = os.path.join(parent_input_dir, name)
        long_name = make_full_name(group_name, name)
        expected_dir = make_expected_dir(template_dir)

        def assert_template(test_case):
            test_case._assert_template(name, long_name, template_dir, expected_dir)

        return assert_template

    return _make_template_tests(group_name, names, parent_input_dir, make_full_name,
                                make_assert_template)


def _make_template_tests(group_name, names, input_dir, make_full_name, make_assert_template):
    """
    Return a list of unittest.TestCase instances.

    """
    class_name = "%sTemplateTestCase" % group_name
    test_case_class = type(class_name, (TemplateTestCaseBase,), {})

    test_cases = []
    for name in names:
        method_name = 'test_%s' % make_full_name(group_name, name)
        assert_template = make_assert_template(group_name, name, input_dir)

        setattr(test_case_class, method_name, assert_template)

        test_case = test_case_class(method_name)
        test_cases.append(test_case)

    return test_cases


class CompareError(Exception):
    pass


class TemplateTestCaseBase(TestCase, AssertFileMixin):

    def _make_compare_message_format(self, expected_dir, actual_dir):
        message_format = dedent("""\
        Directory contents differ:

          Expected | Actual :
            %s
            %s

        %%s

          Context:
        %s

        Test %s: %s""") % (expected_dir, actual_dir, indent(pformat(self.context), "    "),
                           self.template_name, self.description)
        return message_format

    # TODO: remove this method.
    def _raise_compare_error(self, expected_dir, actual_dir, details):
        details = indent(details, "  ")
        msg = """\
Directory contents differ:

  Expected | Actual :
    %s
    %s

%s

  Context: %s

Test %s: %s""" % (expected_dir, actual_dir, details, repr(self.context),
                  self.template_name, repr(self.description))
        raise CompareError(msg)

    def _get_dcmp_attr(self, dcmp, attr_name):
        attr_val = getattr(dcmp, attr_name)
        attr_val = filter(lambda file_name: file_name not in SKIPPED_FILES, attr_val)

        return attr_val

    def _assert_empty(self, dcmp, attr_name, dirs):
        """
        Arguments:

          dcmp: a filecmp.dircmp ("directory comparison") instance.
          attr: an attribute name.
          dirs: a pair (expected_dir, actual_dir)

        """
        attr_val = self._get_dcmp_attr(dcmp, attr_name)
        if not attr_val:
            return

        expected, actual = dirs

        attr_details = "\n".join(["dircmp.%s = %s" % (attr, self._get_dcmp_attr(dcmp, attr)) for
                                  attr in DIRCMP_ATTRS])
        details = ("Attribute %s non-empty for directory compare:\n%s" %
                   (repr(attr_name), indent(attr_details, "  ")))

        self._raise_compare_error(expected, actual, details)

    def _assert_files_equal(self, file_name, file_names, actual_dir, expected_dir):
        actual_path, expected_path = [os.path.join(dir_path, file_name) for dir_path in [actual_dir, expected_dir]]

        details_format = dedent("""\
        Potentially differing files: %s
        Displaying first genuine file difference: %s

        %%s""" % (repr(file_names), file_name))

        def format_file_details(file_details):
            details = details_format % indent(file_details, "  ")
            full_format = self._make_compare_message_format(expected_dir, actual_dir)

            return full_format % details

        self.assertFilesEqual(actual_path, expected_path, format_msg=format_file_details, fuzzy=True,
                              file_encoding=TEST_FILE_ENCODING, errors=DECODE_ERRORS)

    def _assert_diff_files_empty(self, dcmp, expected_dir, actual_dir):
        """
        Arguments:

          dcmp: a filecmp.dircmp ("directory comparison") instance.
          expected: the expected dir.
          actual: the actual dir.

        """
        file_names = self._get_dcmp_attr(dcmp, 'diff_files')
        if not file_names:
            return
        # Otherwise, check whether each individual file may still be the same
        # because of the presence of ellipses  "...".

        index_to_examine = 0
        while file_names:
            file_name = file_names[index_to_examine]
            self._assert_files_equal(file_name, file_names, actual_dir, expected_dir)
            file_names.pop(index_to_examine)
        # If got here, then all files were in fact the same.

    def _assert_dirs_equal(self, expected_dir, actual_dir):
        """
        Raise a CompareError exception if the two directories are unequal.

        """
        dirs = expected_dir, actual_dir
        dcmp = dircmp(*dirs)

        self._assert_diff_files_empty(dcmp, *dirs)
        for attr in DIRCMP_ATTRS:
            self._assert_empty(dcmp, attr, dirs)

        common_dirs = dcmp.common_dirs

        if not common_dirs:
            return

        for subdir in common_dirs:
            expected_subdir = os.path.join(expected_dir, subdir)
            actual_subdir = os.path.join(actual_dir, subdir)
            self._assert_dirs_equal(expected_subdir, actual_subdir)

    def _assert_template(self, template_name, long_name, template_dir, expected_dir):
        """
        Arguments:

          template_name: the name of the template directory.

          input_dir: the directory containing the project directory,
            partials directory, and config file.

        """
        molter = Molter()

        config = molter.read_config(template_dir)
        context = molter.get_context(template_dir)
        description = config['description']

        self.context = context
        self.description = description
        self.template_name = template_name

        with self.util.sandbox_dir(self) as output_dir:
            molter.molt(template_dir=template_dir, output_dir=output_dir)
            self._assert_dirs_equal(expected_dir, output_dir)
