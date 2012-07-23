# encoding: utf-8
#
# Copyright (C) 2012 Chris Jerdonek. All rights reserved.
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
Provides functionality to diff directories recursively.

"""

from __future__ import absolute_import

import filecmp
import os
import sys


class Differ(object):

    @staticmethod
    def contents_match(path1, path2):
        """
        Return whether the file contents at the given paths are the same.

        """
        return filecmp.cmp(path1, path2, shallow=False)

    # TODO: add a "max differences" argument that causes the function
    #   to terminate when that many differences are encountered.
    # TODO: add support for ignoring files matching a certain pattern, etc.
    def __init__(self, match=None, ignore=None):
        """
        Arguments:

          match: a function that accepts two paths and returns whether
            the files at those paths should be considered the same.
            Defaults to Differ.contents_match.

        """
        match_func = Differ.contents_match if match is None else match

        self.ignore = ignore
        self.match = match
        self.match_func = match_func

    def _is_same(self, dcmp, name):
        """
        Return whether the file name in dcmp is a "same file."

        """
        path1, path2 = (os.path.join(path, name) for path in (dcmp.left, dcmp.right))
        return self.match_func(path1, path2)

    def _diff(self, dcmp, results, leading_path=''):
        """
        Recursively compare a filecmp.dircmp instance.

        This method modifies the results container in place.

        Arguments:

          dcmp: a filecmp.dircmp instance.

          results: a three-tuple of (left_only, right_only, diff_files).

          leading_path: a path to prepend to each path added to the
            results container.

        """
        is_different = lambda name: not self._is_same(dcmp, name)
        make_path = lambda name: os.path.join(leading_path, name)

        diff_files = list(dcmp.diff_files)  # make a copy

        if self.match is not None:
            # Then we are using a custom file comparer, which may be more
            # forgiving than the default.  Thus we need to check the
            # different files again to see if any might be the same
            # under the looser condition.
            diff_files[:] = filter(is_different, diff_files)

        # Since dircmp only does "shallow" file comparisons (i.e. doesn't
        # look at file contents), we need to check the files that look
        # the same manually to see if they might in fact be different.
        # See also: http://bugs.python.org/issue15250
        new_diff_files = filter(is_different, dcmp.same_files)
        diff_files.extend(new_diff_files)

        for dir_name, sub_dcmp in dcmp.subdirs.iteritems():
            path = make_path(dir_name)
            self._diff(sub_dcmp, results, leading_path=path)

        name_lists = [dcmp.left_only, dcmp.right_only, diff_files]
        for result_paths, names in zip(results, name_lists):
            paths = [make_path(name) for name in names]
            result_paths.extend(paths)

    def diff(self, dir1, dir2):
        """
        Compare the directories at the given path.

        This method raises an OSError if either directory does not exist.

        """
        # The 3-tuple is (left_only, right_only, diff_files).
        results = tuple([] for i in range(3))

        dcmp = filecmp.dircmp(dir1, dir2, ignore=self.ignore)

        self._diff(dcmp, results)

        # Normalize the results sequences for testing and display purposes.
        map(lambda seq: seq.sort(), results)

        return results