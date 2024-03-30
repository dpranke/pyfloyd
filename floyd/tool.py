# Copyright 2024 Google Inc. All rights reserved.
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

"""A Parser generator and interpreter framework for Python."""

import argparse
import importlib.util
import json
import pathlib
import sys

# If necessary, add ../.. to sys.path so that we can run floyd even when
# it's not installed.
if 'floyd' not in sys.modules and importlib.util.find_spec('floyd') is None:
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

# pylint: disable=wrong-import-position
from floyd.analyzer import Analyzer
from floyd.compiler import Compiler
from floyd.host import Host
from floyd.printer import Printer
from floyd.interpreter import Interpreter
from floyd.parser import Parser
from floyd.version import __version__


def main(argv=None, host=None):
    host = host or Host()

    try:
        args, err = _parse_args(host, argv)
        if err is not None:
            return err

        grammar, err = _read_grammar(host, args)
        if err:
            return err
        if args.pretty_print:
            return _pretty_print_grammar(host, args, grammar)
        if args.ast:
            _write(host, args.output, json.dumps(grammar.ast, indent=2) + '\n')
            return 0
        if args.compile:
            return _write_compiled_grammar(host, args, grammar)
        return _interpret_grammar(host, args, grammar)

    except KeyboardInterrupt:
        host.print('Interrupted, exiting ...', file=host.stderr)
        return 130  # SIGINT

    return 0


def _parse_args(host, argv):
    ap = argparse.ArgumentParser(prog='floyd')
    ap.add_argument(
        '-a',
        '--ast',
        action='store_true',
        help='dump the ast of the parsed input',
    )
    ap.add_argument(
        '-c',
        '--compile',
        action='store_true',
        help='compile grammar instead of interpreting it',
    )
    ap.add_argument(
        '-i', '--input', default='-', help='path to read data from'
    )
    ap.add_argument('-o', '--output', help='path to write output to')
    ap.add_argument(
        '-p',
        '--pretty-print',
        action='store_true',
        help='pretty-print the input grammar',
    )
    ap.add_argument(
        '-V',
        '--version',
        action='store_true',
        help='print current version (%s)' % __version__,
    )
    ap.add_argument(
        '--class-name',
        default='Parser',
        help='class name for the generated class when '
        'compiling it (defaults to "Parser")',
    )
    ap.add_argument(
        '--memoize',
        action='store_true',
        default=True,
        help='memoize intermediate results (on by default)',
    )
    ap.add_argument('--no-memoize', dest='memoize', action='store_false')
    ap.add_argument(
        '--main',
        action='store_true',
        default=True,
        help='generate a main() wrapper (on by default)',
    )
    ap.add_argument('--no-main', dest='main', action='store_false')
    ap.add_argument(
        'grammar',
        nargs='?',
        help='grammar file to interpret or compiled. '
        'Usually a required argument.',
    )

    args = ap.parse_args(argv)

    if args.version:
        host.print(__version__)
        return None, 0

    if not args.grammar:
        host.print('You must specify a grammar.')
        return None, 2

    if not args.output:
        if args.compile:
            args.output = host.splitext(host.basename(args.grammar))[0] + '.py'
        else:
            args.output = '-'

    return args, None


def _read_grammar(host, args):
    if not host.exists(args.grammar):
        host.print(
            'Error: no such file: "%s"' % args.grammar, file=host.stderr
        )
        return None, 1

    try:
        grammar_txt = host.read_text_file(args.grammar)
    except Exception as e:
        host.print('Error: %s' % str(e), file=host.stderr)
        return None, 1

    parser = Parser(grammar_txt, args.grammar)
    ast, err, _ = parser.parse()
    if err:
        host.print(err, file=host.stderr)
        return None, 1

    grammar, err = Analyzer().analyze(ast)
    if err:
        host.print(err, file=host.stderr)
        return None, 1
    return grammar, 0


def _pretty_print_grammar(host, args, grammar):
    contents, err = Printer(grammar).dumps(), None
    if err:
        host.print(err, file=host.stderr)
        return 1
    _write(host, args.output, contents)
    return 0


def _write_compiled_grammar(host, args, grammar):
    comp = Compiler(grammar, args.class_name, args.main, args.memoize)
    contents, err = comp.compile()
    if err:
        host.print(err, file=host.stderr)
        return 1
    _write(host, args.output, contents)
    if args.main:
        host.make_executable(args.output)
    return 0


def _interpret_grammar(host, args, grammar):
    if args.input == '-':
        path, contents = ('<stdin>', host.stdin.read())
    else:
        path, contents = (args.input, host.read_text_file(args.input))

    out, err = Interpreter(grammar, args.memoize).interpret(contents, path)[:2]
    if err:
        host.print(err, file=host.stderr)
        return 1

    out = json.dumps(out, indent=2, sort_keys=True)

    _write(host, args.output, out + '\n')
    return 0


def _write(host, path, contents):
    if path == '-':
        host.print(contents, end='')
    else:
        host.write_text_file(path, contents)


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
