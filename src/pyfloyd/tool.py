#!/usr/bin/env python
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
import io
import json
import os
import pathlib
import pprint
import sys

# If necessary, add ../.. to sys.path so that we can run pyfloyd even when
# it's not installed.
if (
    'pyfloyd' not in sys.modules
    and importlib.util.find_spec('pyfloyd') is None
):
    sys.path.insert(
        0, str(pathlib.Path(__file__).parent.parent)
    )  # pragma: no cover

# pylint: disable=wrong-import-position
import pyfloyd
from pyfloyd import generator
from pyfloyd.host import Host


def main(argv=None, host=None):
    host = host or Host()

    try:
        args, err = _parse_args(host, argv)
        if err is not None:
            return err

        grammar, err = _read_grammar(host, args)
        if err:
            host.print(err, file=host.stderr)
            return 1

        externs = {}
        for d in args.define:
            k, v = d.split('=', 1)
            externs[k] = json.loads(v)

        if args.ast:
            ast, err = pyfloyd.dump_ast(
                grammar,
                args.grammar,
                rewrite_filler=args.rewrite_filler,
                rewrite_subrules=args.rewrite_subrules,
            )
            if ast:
                s = io.StringIO()
                pprint.pprint(ast, stream=s)
                contents = s.getvalue()
            else:
                contents = None
        elif args.pretty_print:
            contents, err = pyfloyd.pretty_print(
                grammar, args.grammar, args.rewrite_filler
            )
        elif args.compile:
            if not args.language:
                args.language = pyfloyd.DEFAULT_LANGUAGE
            options = pyfloyd.GeneratorOptions(
                language=args.language, main=args.main, memoize=args.memoize
            )
            contents, err, _ = pyfloyd.generate(
                grammar, path=args.grammar, options=options
            )
        else:
            contents, err, _ = _interpret_grammar(host, args, grammar, externs)

        if err:
            host.print(err, file=host.stderr)
            return 1
        _write(host, args.output, contents)
        if args.compile and args.main:
            host.make_executable(args.output)
        return 0

    except KeyboardInterrupt:
        host.print('Interrupted, exiting.', file=host.stderr)
        return 130  # SIGINT


def _parse_args(host, argv):
    ap = argparse.ArgumentParser(prog='pyfloyd')
    generator.add_language_arguments(ap)
    ap.add_argument(
        '--ast', action='store_true', help='dump the parsed AST of the grammar'
    )
    ap.add_argument(
        '-c',
        '--compile',
        action='store_true',
        help='compile grammar instead of interpreting it',
    )
    ap.add_argument(
        '-D',
        '--define',
        action='append',
        metavar='var=val',
        default=[],
        help='Define an external var=value',
    )
    ap.add_argument(
        '-o', '--output', metavar='path', help='path to write output to'
    )
    ap.add_argument(
        '-p',
        '--pretty-print',
        action='store_true',
        help='pretty-print the input grammar',
    )
    ap.add_argument(
        '--rewrite-filler',
        action='store_true',
        help='include the filler rules in the grammar',
    )
    ap.add_argument(
        '--rewrite-subrules',
        action='store_true',
        help='Extract subnodes into their own rules as needed',
    )
    ap.add_argument(
        '-V',
        '--version',
        action='store_true',
        help='print current version (%s)' % pyfloyd.__version__,
    )
    ap.add_argument(
        '-M',
        '--memoize',
        action='store_true',
        default=False,
        help='memoize intermediate results (off by default)',
    )
    ap.add_argument('--no-memoize', dest='memoize', action='store_false')
    ap.add_argument(
        '-m',
        '--main',
        action='store_true',
        default=False,
        help='generate a main() wrapper (off by default)',
    )
    ap.add_argument('--no-main', dest='main', action='store_false')
    ap.add_argument(
        'grammar',
        nargs='?',
        help='grammar file to interpret or compiled. '
        'Usually a required argument.',
    )
    ap.add_argument(
        'input', nargs='?', default='-', help='path to read data from'
    )

    args = ap.parse_args(argv)

    if args.version:
        host.print(pyfloyd.__version__)
        return None, 0

    if not args.grammar:
        host.print('You must specify a grammar.')
        return None, 2

    if not args.output:
        if args.compile:
            if not args.language:
                args.language = generator.DEFAULT_LANGUAGE
            ext = generator.LANG_TO_EXT[args.language]
            args.output = host.splitext(args.grammar)[0] + ext
        else:
            args.output = '-'
    elif not args.language:
        if not args.language:
            ext = os.path.splitext(args.output)[1]
            args.language = generator.EXT_TO_LANG[ext]

    return args, None


def _read_grammar(host, args):
    if not host.exists(args.grammar):
        return None, 'Error: no such file: "%s"' % args.grammar

    try:
        grammar_txt = host.read_text_file(args.grammar)
        return grammar_txt, None
    except Exception as e:
        return None, 'Error reading "%s": %s' % (args.grammar, str(e))


def _interpret_grammar(host, args, grammar, externs):
    if args.input == '-':
        path, contents = ('<stdin>', host.stdin.read())
    else:
        path, contents = (args.input, host.read_text_file(args.input))

    out, err, endpos = pyfloyd.parse(
        grammar,
        contents,
        grammar_path=args.grammar,
        path=path,
        externs=externs,
        memoize=args.memoize,
    )
    if err:
        return None, err, endpos

    out = json.dumps(out, indent=2, sort_keys=True) + '\n'
    return out, None, endpos


def _write(host, path, contents):
    if path == '-':
        host.print(contents, end='')
    else:
        host.write_text_file(path, contents)


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
