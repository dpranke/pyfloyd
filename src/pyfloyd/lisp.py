# Copyright 2025 Dirk Pranke. All rights reserved.
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
"""A bare-bones Lisp interpreter."""

import argparse
import sys
from typing import Any

from pyfloyd import lisp_interpreter
from pyfloyd import lisp_parser


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--code')
    parser.add_argument('file', nargs='?')
    args = parser.parse_args(argv)

    interp = lisp_interpreter.Interpreter()
    if args.code:
        text = args.code
        source = '<code>'
        repl = False
    elif args.file:
        if args.file == '-':
            text = sys.stdin.read()
            source = '<stdin>'
        else:
            with open(args.file, encoding='utf-8') as fp:
                text = fp.read()
            source = args.file
        repl = False
    else:
        repl = True
        source = '<repl>'
        print('> ', end='')
        try:
            text = input()
        except KeyboardInterrupt:
            print('interrupted, exiting', file=sys.stderr)
            return 130
        except EOFError:
            return 0

    while True:
        if not text:
            break

        exprs, err, _ = lisp_parser.parse(text, source)
        if err:
            print(err, file=sys.stderr)
            return 1
        try:
            for expr in exprs:
                v = interp.eval(expr)
                print(schemestr(v))

            if not repl:
                break

            print('> ', end='')
            text = input()
        except lisp_interpreter.InterpreterError as e:
            print(e, file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print('interrupted, exiting', file=sys.stderr)
            return 130
        except EOFError:
            pass

    return 0


def schemestr(val: Any) -> str:
    if val is True:
        return '#t'
    if val is False:
        return '#f'
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        return f'"{val}"'
    assert isinstance(val, list)
    if len(val) and val[0] == 'symbol':
        return val[1]
    s = "'("
    for i, v in enumerate(val):
        s += schemestr(v)
        if i < len(val) - 1:
            s += ' '
    s += ')'
    return s


if __name__ == '__main__':
    sys.exit(main(sys.argv))
