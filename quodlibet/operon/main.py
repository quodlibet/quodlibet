# Copyright 2012,2013 Christoph Reiter
#                2023 Nick Boultbee
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import os
from optparse import OptionParser

import quodlibet
from quodlibet import const
from quodlibet.util.dprint import print_

from .base import Command, CommandError
from . import commands

commands  # noqa


def _print_help(main_cmd, parser, file=None):
    """Print a short help list for all commands"""

    if file is None:
        file = sys.stdout

    parser.print_help(file=file)

    cl = ["", "Commands:"]
    for command in Command.COMMANDS:
        cl.append("   %-17s %s" % (command.NAME, command.DESCRIPTION))
    cl.append("")
    cl.append("See '%s help <command>' for more information "
              "on a specific command." % main_cmd)

    print_("\n".join(cl), file=file)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    quodlibet.init_cli()

    main_cmd = os.path.basename(argv[0])

    # the main optparser
    usage = "%s [--version] [--help] [--verbose] <command> [<args>]" % main_cmd
    parser = OptionParser(usage=usage)

    parser.remove_option("--help")
    parser.add_option("-h", "--help", action="store_true")
    parser.add_option("--version", action="store_true",
                      help="print version")
    parser.add_option("-v", "--verbose", action="store_true",
                      help="verbose output")

    # no args, print help (might change in the future)
    if len(argv) <= 1:
        _print_help(main_cmd, parser, file=sys.stderr)
        return 1

    # collect options for the main command and get the command offset
    offset = -1
    pre_command = []
    for i, a in enumerate(argv):
        if i == 0:
            continue
        elif a.startswith("-"):
            pre_command.append(a)
        else:
            offset = i
            break

    # parse the global options
    options = parser.parse_args(pre_command)[0]

    # --help somewhere
    if options.help:
        _print_help(main_cmd, parser)
        return 0

    # --version somewhere
    if options.version:
        print_("%s version %s" % (main_cmd, const.VERSION))
        return 0

    # no sub command followed, help to stderr
    if offset == -1:
        _print_help(main_cmd, parser, file=sys.stderr)
        return 1
    arg = argv[offset]

    # special case help and list all commands
    if arg == "help":
        # no command, list all commands
        if len(argv) == 2:
            _print_help(main_cmd, parser)
            return 0

    # get the right sub command and pass the remaining args
    for command in Command.COMMANDS:
        if command.NAME == arg:
            cmd = command(main_cmd, options)
            try:
                cmd.execute(argv[offset + 1:])
            except CommandError as e:
                print_(u"%s: %s" % (command.NAME, e), file=sys.stderr)
                return 1
            break
    else:
        print_(u"Unknown command '%s'. See '%s help'." % (arg, main_cmd),
               file=sys.stderr)
        return 1

    return 0
