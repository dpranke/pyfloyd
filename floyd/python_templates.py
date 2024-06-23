# Copyright 2024 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 as found in the LICENSE file.
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


DEFAULT_HEADER = """\
from typing import Any, NamedTuple, Optional
{unicodedata_import}
# pylint: disable=too-many-lines


"""


DEFAULT_FOOTER = ''


MAIN_HEADER = """\
#!/usr/bin/env python

import argparse
import json
import os
import sys
from typing import Any, NamedTuple, Optional
{unicodedata_import}

# pylint: disable=too-many-lines


def main(
    argv=sys.argv[1:],
    stdin=sys.stdin,
    stdout=sys.stdout,
    stderr=sys.stderr,
    exists=os.path.exists,
    opener=open,
):
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('file', nargs='?')
    args = arg_parser.parse_args(argv)

    if not args.file or args.file[1] == '-':
        path = '<stdin>'
        fp = stdin
    elif not exists(args.file):
        print('Error: file "%s" not found.' % args.file, file=stderr)
        return 1
    else:
        path = args.file
        fp = opener(path)

    msg = fp.read()
    result = parse(msg, path)
    if result.err:
        print(result.err, file=stderr)
        return 1
    print(json.dumps(result.val, indent=2), file=stdout)
    return 0


"""


MAIN_FOOTER = """\


if __name__ == '__main__':
    sys.exit(main())
"""


PARSING_RUNTIME_EXCEPTION = """\
class _ParsingRuntimeError(Exception):
    pass


"""

OPERATOR_CLASS = """\
class _OperatorState:
    def __init__(self):
        self.current_depth = 0
        self.current_prec = 0
        self.prec_ops = {}
        self.precs = []
        self.rassoc = set()
        self.choices = {}


"""

CLASS = """\
class Result(NamedTuple):
    \"\"\"The result returned from a `parse()` call.

    If the parse is successful, `val` will contain the returned value, if any
    and `pos` will indicate the point in the text where the parser stopped.
    If the parse is unsuccessful, `err` will contain a string describing
    any errors that occurred during the parse and `pos` will indicate
    the location of the farthest error in the text.
    \"\"\"

    val: Any = None
    err: Optional[str] = None
    pos: Optional[int] = None


def parse(text: str, path: str = '<string>') -> Result:
    \"\"\"Parse a given text and return the result.

    If the parse was successful, `result.val` will be the returned value
    from the parse, and `result.pos` will indicate where the parser
    stopped when it was done parsing.

    If the parse is unsuccessful, `result.err` will be a string describing
    any errors found in the text, and `result.pos` will indicate the
    furthest point reached during the parse.

    If the optional `path` is provided it will be used in any error
    messages to indicate the path to the filename containing the given
    text.
    \"\"\"
    return _Parser(text, path).parse()


class _Parser:
    def __init__(self, text, path):
        self.text = text
        self.end = len(self.text)
        self.errpos = 0
        self.ok = True
        self.path = path
        self.pos = 0
        self.val = None
"""


PARSE = """\
    def parse(self):
        self._{starting_rule}_()
        if not self.ok:
            return Result(None, self._err_str(), self.errpos)
        return Result(self.val, None, self.pos)
"""


PARSE_WITH_EXCEPTION = """\
    def parse(self):
        try:
            self._{starting_rule}_()
            if not self.ok:
                return None, self._err_str(), self.errpos
            return self.val, None, self.pos
        except _ParsingRuntimeError as e:  # pragma: no cover
            lineno, _ = self._err_offsets()
            return (
                None,
                self.path + ':' + str(lineno) + ' ' + str(e),
                self.errpos,
            )
"""


BUILTINS = """\
    def _any_(self):
        if self.pos < self.end:
            self._succeed(self.text[self.pos], self.pos + 1)
        else:
            self._fail()

    def _cat(self, strs):
        return ''.join(strs)

    def _ch(self, ch):
        p = self.pos
        if p < self.end and self.text[p] == ch:
            self._succeed(ch, self.pos + 1)
        else:
            self._fail()

    def _dict(self, pairs):
         return dict(pairs)

    def _end_(self):
        if self.pos == self.end:
            self._succeed(None)
        else:
            self._fail()

    def _err_offsets(self):
        lineno = 1
        colno = 1
        for i in range(self.errpos):
            if self.text[i] == '\\n':
                lineno += 1
                colno = 1
            else:
                colno += 1
        return lineno, colno

    def _err_str(self):
        lineno, colno = self._err_offsets()
        if self.errpos == len(self.text):
            thing = 'end of input'
        else:
            thing = '"%s"' % self.text[self.errpos]
        return '%s:%d Unexpected %s at column %d' % (
            self.path,
            lineno,
            thing,
            colno,
        )

    def _fail(self):
        self.val = None
        self.ok = False
        self.errpos = max(self.errpos, self.pos)

    def _float(self, str):
          if '.' in str or 'e' in str or 'E' in str:
              return float(str)
          else:
              return int(str)

    def _get(self, var):
        return self.scopes[-1][var]

    def _hex(self, str):
        return int(str, base=16)

    def _is_unicat(self, var, cat):
        return unicodedata.category(var) == cat

    def _itou(self, n):
        return chr(n)

    def _join(self, s, vs):
        return s.join(vs)

    def _leftrec(self, rule, rule_name, left_assoc):
        pos = self.pos
        key = (rule_name, pos)
        seed = self.seeds.get(key)
        if seed:
            self.val, self.ok, self.pos = seed
            return
        if rule_name in self.blocked:
            self.val = None
            self.ok = False
            return
        current = (None, False, self.pos)
        self.seeds[key] = current
        if left_assoc:
            self.blocked.add(rule_name)
        while True:
            rule()
            if self.pos > current[2]:
                current = (self.val, self.ok, self.pos)
                self.seeds[key] = current
                self.pos = pos
            else:
                del self.seeds[key]
                self.val, self.ok, self.pos = current
                if left_assoc:
                    self.blocked.remove(rule_name)
                return

    def _operator(self, rule_name):
        o = self.operators[rule_name]
        pos = self.pos
        key = (rule_name, self.pos)
        seed = self.seeds.get(key)
        if seed:
            self.val, self.ok, self.pos = seed
            return
        o.current_depth += 1
        current = (None, False, self.pos)
        self.seeds[key] = current
        min_prec = o.current_prec
        i = 0
        while i < len(o.precs):
            repeat = False
            prec = o.precs[i]
            prec_ops = o.prec_ops[prec]
            if prec < min_prec:
                break
            o.current_prec = prec
            if prec_ops[0] not in o.rassoc:
                o.current_prec += 1
            for j, _ in enumerate(prec_ops):
                op = prec_ops[j]
                o.choices[op]()
                if self.ok and self.pos > pos:
                    current = (self.val, self.ok, self.pos)
                    self.seeds[key] = current
                    repeat = True
                    break
                self._rewind(pos)
            if not repeat:
                i += 1

        del self.seeds[key]
        o.current_depth -= 1
        if o.current_depth == 0:
            o.current_prec = 0
        self.val, self.ok, self.pos = current

    def _range(self, i, j):
        p = self.pos
        if p != self.end and ord(i) <= ord(self.text[p]) <= ord(j):
            self._succeed(self.text[p], self.pos + 1)
        else:
            self._fail()

    def _rewind(self, newpos):
        self._succeed(None, newpos)

    def _set(self, var, val):
        self.scopes[-1][var] = val

    def _str(self, s):
        for ch in s:
            self._ch(ch)
            if not self.ok:
                return
        self.val = s

    def _succeed(self, v, newpos=None):
        self.val = v
        self.ok = True
        if newpos is not None:
            self.pos = newpos

    def _unicat(self, cat):
        p = self.pos
        if p < self.end and unicodedata.category(self.text[p]) == cat:
            self._succeed(self.text[p], self.pos + 1)
        else:
            self._fail()

    def _utoi(self, s):
        return ord(s)

    def _xtoi(self, s):
        return int(s, base=16)

    def _xtou(self, s):
        return chr(int(s, base=16))
"""
