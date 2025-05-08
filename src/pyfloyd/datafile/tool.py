# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A tool to parse and pretty-print Floyd datafiles.

Usage:

    $ echo '{foo:"bar"}' | python -m pyfloyd.datafile
    {
        foo: bar,
    }
    $ echo '{foo:"bar"}' | python -m pyfloyd.datafile --as-json
    {
        "foo": "bar"
    }
"""

import argparse
import json
import os
import sys

try:
    import pyfloyd
except ModuleNotFoundError:  # pragma: no cover
    src_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sys.path.insert(0, src_dir)
    import pyfloyd

import pyfloyd.datafile
import pyfloyd.support


def main(argv=None, host=None):
    host = host or pyfloyd.support.Host()

    args = _parse_args(host, argv)

    if args.version:
        host.print(pyfloyd.__version__)
        return 0

    if args.cmd:
        inp = args.cmd
    elif args.file == '-':
        inp = host.stdin.read()
    else:
        inp = host.read_text_file(args.file)

    if args.indent == 'None':
        args.indent = None
    else:
        try:
            args.indent = int(args.indent)
        except ValueError:
            pass

    obj = pyfloyd.datafile.loads(inp)
    if args.as_json:
        s = json.dumps(obj, indent=args.indent)
    else:
        s = pyfloyd.datafile.dumps(obj, indent=args.indent)
    host.print(s)
    return 0


class _HostedArgumentParser(argparse.ArgumentParser):
    """An argument parser that plays nicely w/ host objects."""

    def __init__(self, host, **kwargs):
        self.host = host
        super().__init__(**kwargs)

    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, self.host.stderr)
        sys.exit(status)

    def error(self, message):
        self.host.print(f'usage: {self.usage}', end='', file=self.host.stderr)
        self.host.print('    -h/--help for help\n', file=self.host.stderr)
        self.exit(2, f'error: {message}\n')

    def print_help(self, file=None):
        self.host.print(self.format_help(), file=file)


def _parse_args(host, argv):
    usage = 'fdf [options] [FILE]\n'

    parser = _HostedArgumentParser(
        host,
        prog='fdf',
        usage=usage,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '-V',
        '--version',
        action='store_true',
        help=f'show version ({pyfloyd.__version__})',
    )
    parser.add_argument(
        '-c',
        metavar='STR',
        dest='cmd',
        help='inline string to read instead of reading from a file',
    )
    parser.add_argument(
        '--as-json',
        dest='as_json',
        action='store_const',
        const=True,
        default=False,
        help='output as JSON',
    )
    parser.add_argument(
        '--indent',
        dest='indent',
        default=4,
        help='amount to indent each line (default is 4 spaces)',
    )
    parser.add_argument(
        'file',
        metavar='FILE',
        nargs='?',
        default='-',
        help='optional file to read document from; if '
        'not specified or "-", will read from stdin '
        'instead',
    )
    return parser.parse_args(argv)


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
