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
import json
import pathlib
import pdb
import sys
import traceback

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
from pyfloyd import datafile, support


def main(argv=None, host=None):
    host = host or support.Host()

    args = None
    try:
        args, err = _parse_args(host, argv)

        if err is not None:
            return err

        grammar, err = _read_grammar(host, args)
        if err:
            host.print(err, file=host.stderr)
            return 1

        externs = {}
        for exts in args.externs:
            d = datafile.loads(exts)
            externs.update(d)

        options = pyfloyd.generator_options_from_args(args, argv)
        contents = None
        ext = None
        if args.ast or args.full_ast:
            ast, err = pyfloyd.dump_ast(
                grammar,
                args.grammar,
                rewrite_subrules=args.rewrite_subrules,
            )
            if ast:
                contents = json.dumps(ast.to_json(args.full_ast), indent=2)
        elif args.pretty_print:
            contents, err = pyfloyd.pretty_print(grammar, args.grammar)
        elif args.interpret:
            contents, err, _ = _interpret_grammar(
                host, args, grammar, externs, options
            )
            ext = None
        else:
            if args.template is None:
                if args.output and args.output != '-':
                    ext = host.splitext(args.output)[1]
                    args.template = pyfloyd.KNOWN_TEMPLATES.get(ext)
            v, err, _ = pyfloyd.generate(
                grammar, path=args.grammar, options=options
            )
            if v is not None:
                contents, ext = v

        if err:
            host.print(err, file=host.stderr)
            return 1
        path = _write(host, args, contents, ext)
        if not args.interpret and args.main and path != '-':
            host.make_executable(path)
        return 0

    except KeyboardInterrupt:  # pragma: no cover
        host.print('Interrupted, exiting.', file=host.stderr)
        return 130  # SIGINT
    except datafile.DatafileError as exc:  # pragma: no cover
        if args and args.post_mortem:
            traceback.print_exception(exc)
            pdb.post_mortem()
        print(str(exc), file=host.stderr)
        return 1
    # pylint: disable=broad-exception-caught
    except Exception as exc:  # pragma: no cover
        # pragma: no cover
        if args and args.post_mortem:
            traceback.print_exception(exc)
            pdb.post_mortem()
        else:
            raise exc
        return 1


def _parse_args(host, argv):
    ap = argparse.ArgumentParser(prog='pyfloyd')
    pyfloyd.add_generator_arguments(ap)
    ap.add_argument(
        '--ast', action='store_true', help='dump the parsed AST of the grammar'
    )
    ap.add_argument(
        '--full-ast',
        action='store_true',
        help='dump the full AST of the grammar including derived attributes',
    )
    ap.add_argument(
        '--as-json', action='store_true', help='dump the AST as JSON'
    )
    ap.add_argument(
        '-E',
        '--externs',
        action='append',
        metavar='datafile-string',
        default=[],
        help='options for the grammar (specified as %%externs in the grammar)',
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
        help=f'print current version ({pyfloyd.__version__})',
    )
    ap.add_argument(
        'grammar', nargs='?', help='grammar file to interpret or compile'
    )
    ap.add_argument(
        '-I',
        '--interpret',
        action='store_true',
        help='interpret the grammar instead of compiling it',
    )
    ap.add_argument(
        '-i',
        '--input',
        action='store',
        default='-',
        help='path to read data from',
    )
    ap.add_argument('--post-mortem', '--pm', action='store_true')

    args = ap.parse_args(argv)

    if args.version:
        host.print(pyfloyd.__version__)
        return None, 0

    if not args.grammar:
        host.print('You must specify a grammar.')
        return None, 2

    if not args.output and (args.interpret or args.pretty_print):
        args.output = '-'

    return args, None


def _read_grammar(host, args):
    if not host.exists(args.grammar):
        return None, f'Error: no such file: "{args.grammar}"'

    grammar_txt = host.read_text_file(args.grammar)
    return grammar_txt, None


def _interpret_grammar(host, args, grammar, externs, options):
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
        memoize=options.memoize,
    )
    if err:
        return None, err, endpos

    out = json.dumps(out, indent=2, sort_keys=True) + '\n'
    return out, None, endpos


def _write(host, args, contents, ext):
    if args.output and args.output != '-':
        host.write_text_file(args.output, contents)
        return args.output

    if args.output == '-':
        host.print(contents, end='')
        return '-'
    path = host.splitext(args.grammar)[0] + ext
    host.write_text_file(path, contents)
    return path


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
