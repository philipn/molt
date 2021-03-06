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
Supplies the main method for the `molt` command entry point.

This module is a wrapper around another main method.  We use this wrapper
to let us configure logging with minimal amount of code imported (in
particular, before importing the bulk of the molt package).  This lets
us log statements about conditional imports more easily (e.g. whether
yaml has loaded as a replacement for json, etc).  Otherwise, logging
would not get configured after all those imports have already taken place.

"""

from __future__ import absolute_import

import logging
import sys
import traceback

from molt.general.error import Error
from molt import constants
from molt.scripts.molt import argparsing
from molt.scripts.molt.argparsing import OPTION_HELP
import molt.scripts.molt.general.logconfig as logconfig
from molt.scripts.molt.general.optionparser import UsageError
from molt.test.harness import test_logger


LOGGING_LEVEL_DEFAULT = logging.INFO

_app_log = logging.getLogger("molt.app")
_log = logging.getLogger(__name__)


class _Writer(object):

    def __init__(self, write):
        self.write = write


def _make_writer(output_log):
    write = lambda msg: output_log.info(msg)
    return _Writer(write)


def _configure_output_logger(stream):
    """Configure a special logger for non-diagnostic application output."""
    configurer = logconfig.LogConfigurer(stream=stream)
    handler = configurer.make_handler("molt: %(message)s")
    # TODO: put this string constant somewhere else.
    log = logging.getLogger("molt.output")
    log.propagate = False
    log.setLevel(logging.INFO)
    log.addHandler(handler)
    return log


def _configure_logging(sys_argv, sys_stderr=None):
    """
    Configure logging and return whether to run in verbose mode.

    """
    if sys_stderr is None:
        sys_stderr = sys.stderr

    logging_level = LOGGING_LEVEL_DEFAULT
    is_running_tests = False
    succinct_logging = False
    verbose = False

    # TODO: follow all of the recommendations here:
    # http://www.artima.com/weblogs/viewpost.jsp?thread=4829

    # Configure logging before parsing arguments for real.
    ns = argparsing.preparse_args(sys_argv)

    if ns is not None:
        # Then args parsed without error.
        verbose = ns.verbose
        if verbose:
            logging_level = logging.DEBUG
        if ns.run_test_mode:
            is_running_tests = True
        if ns.succinct_logging:
            succinct_logging = True

    # Do not use ns below this block in case of argparsing errors above.

    # We pass a newline as last_text to prevent a newline from being added
    # before the first log message.
    log_stream = logconfig.RememberingStream(sys_stderr, last_text='\n')

    output_log = _configure_output_logger(stream=log_stream)

    # Set the loggers to display during test runs.
    if is_running_tests:
        # TODO: tighten the list of names to allow.
        names = [logconfig.__name__, _app_log.name, test_logger.name]
    elif succinct_logging:
        # Let the error-catching logger log.
        # TODO: add a test for this.
        names = [_log.name]
    else:
        names = ['']

    logconfig.configure_logging(logging_level, stderr=log_stream, names=names)

    if is_running_tests:
        output_log.info("allowed logs: %s" % ", ".join(names))
    elif succinct_logging:
        output_log.info("diagnostic logs suppressed")
    else:
        names = ['']

    writer = _make_writer(output_log)

    return verbose, log_stream, writer


def log_error(details, verbose):
    if verbose:
        msg = traceback.format_exc()
    else:
        msg = """\
%s
Pass %s for the stack trace.""" % (details,
                                   argparsing.OPTION_VERBOSE.display(' or '))
    _log.error(msg)


def run_molt(sys_argv, from_source=False, configure_logging=_configure_logging,
             process_args=None, **kwargs):
    """
    Execute this script's main function, and return the exit status.

    Args:

      from_source: whether or not the script was initiated from a source
        checkout (e.g. by calling `python -m molt.scripts.molt` as
        opposed to via an installed setup entry point).

      process_args: the function called within this method's try-except
        block and that accepts sys.argv as a single parameter.
        This parameter is exposed only for unit testing purposes.  It
        allows the function's exception handling logic to be tested
        more easily.

    """
    verbose, log_stream, writer = configure_logging(sys_argv)

    _app_log.debug("sys.argv: %s" % repr(sys_argv))
    _app_log.debug("kwargs: %s" % repr(kwargs))

    try:
        if process_args is None:
            # See this module's docstring for an explanation of why
            # we do this import inside a function body.
            # TODO: we should not need to do this import here?
            from molt.scripts.molt.argprocessor import run_args
            process_args = run_args
        status = process_args(sys_argv, writer=writer,
                              test_runner_stream=log_stream,
                              from_source=from_source)
    # TODO: include KeyboardInterrupt in the template version of this file.
    except UsageError as err:
        details = """\
Command-line usage error: %s
-->%s

Pass %s for help documentation and available options.""" % (
            err, repr(sys.argv), OPTION_HELP.display(' or '))
        log_error(details, verbose)
        status = constants.EXIT_STATUS_USAGE_ERROR
    except Error, err:
        log_error(err, verbose)
        status = constants.EXIT_STATUS_FAIL

    return status

def main(sys_argv=None, from_source=False, **kwargs):
    """
    Arguments:

      from_source: whether this function is being called from a source
        checkout (e.g. by running `python runmolt.py` or
        `python -m molt.scripts.molt`).

    """
    if sys_argv is None:
        sys_argv = sys.argv
    result = run_molt(sys_argv=sys_argv, from_source=from_source, **kwargs)
    sys.exit(result)
