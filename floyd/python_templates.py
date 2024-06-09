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
{unicodedata_import}# pylint: disable=too-many-lines


"""


DEFAULT_FOOTER = ''


MAIN_HEADER = """\
#!/usr/bin/env python

import argparse
import json
import os
import sys
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
        fname = '<stdin>'
        fp = stdin
    elif not exists(args.file):
        print('Error: file "%s" not found.' % args.file, file=stderr)
        return 1
    else:
        fname = args.file
        fp = opener(fname)

    msg = fp.read()
    obj, err, _ = {classname}(msg, fname).parse()
    if err:
        print(err, file=stderr)
        return 1
    print(json.dumps(obj, indent=2), file=stdout)
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
class {classname}:
    def __init__(self, msg, fname):
        self.msg = msg
        self.end = len(self.msg)
        self.errpos = 0
        self.failed = False
        self.fname = fname
        self.pos = 0
        self.val = None
"""


PARSE = """\
    def parse(self):
        self._{starting_rule}_()
        if self.failed:
            return None, self._err_str(), self.errpos
        return self.val, None, self.pos
"""


PARSE_WITH_EXCEPTION = """\
    def parse(self):
        try:
            self._{starting_rule}_()
            if self.failed:
                return None, self._err_str(), self.errpos
            return self.val, None, self.pos
        except _ParsingRuntimeError as e:  # pragma: no cover
            lineno, _ = self._err_offsets()
            return (
                None,
                self.fname + ':' + str(lineno) + ' ' + str(e),
                self.errpos,
            )
"""


BUILTINS = """\
    def _any_(self):
        if self.pos < self.end:
            self._succeed(self.msg[self.pos], self.pos + 1)
        else:
            self._fail()

    def _bind(self, rule, var):
        rule()
        if not self.failed:
            self._set(var, self.val)

    def _cat(self, strs):
        return ''.join(strs)

    def _ch(self, ch):
        p = self.pos
        if p < self.end and self.msg[p] == ch:
            self._succeed(ch, self.pos + 1)
        else:
            self._fail()

    def _choose(self, rules):
        p = self.pos
        for rule in rules[:-1]:
            rule()
            if not self.failed:
                return
            self._rewind(p)
        rules[-1]()

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
            if self.msg[i] == '\\n':
                lineno += 1
                colno = 1
            else:
                colno += 1
        return lineno, colno

    def _err_str(self):
        lineno, colno = self._err_offsets()
        if self.errpos == len(self.msg):
            thing = 'end of input'
        else:
            thing = '"%s"' % self.msg[self.errpos]
        return '%s:%d Unexpected %s at column %d' % (
            self.fname,
            lineno,
            thing,
            colno,
        )

    def _fail(self):
        self.val = None
        self.failed = True
        self.errpos = max(self.errpos, self.pos)

    def _float(self, str):
          if '.' in str or 'e' in str or 'E' in str:
              return float(str)
          else:
              return int(str)

    def _get(self, var):
        return self.scopes[-1][1][var]

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
            self.val, self.failed, self.pos = seed
            return
        if rule_name in self.blocked:
            self.val = None
            self.failed = True
            return
        current = (None, True, self.pos)
        self.seeds[key] = current
        if left_assoc:
            self.blocked.add(rule_name)
        while True:
            rule()
            if self.pos > current[2]:
                current = (self.val, self.failed, self.pos)
                self.seeds[key] = current
                self.pos = pos
            else:
                del self.seeds[key]
                self.val, self.failed, self.pos = current
                if left_assoc:
                    self.blocked.remove(rule_name)
                return

    def _not(self, rule):
        p = self.pos
        errpos = self.errpos
        rule()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _operator(self, rule_name):
        o = self.operators[rule_name]
        pos = self.pos
        key = (rule_name, self.pos)
        seed = self.seeds.get(key)
        if seed:
            self.val, self.failed, self.pos = seed
            return
        o.current_depth += 1
        current = (None, True, self.pos)
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
                if not self.failed and self.pos > pos:
                    current = (self.val, self.failed, self.pos)
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
        self.val, self.failed, self.pos = current

    def _opt(self, rule):
        p = self.pos
        rule()
        if self.failed:
            self._succeed([], p)
        else:
            self._succeed([self.val])

    def _plus(self, rule):
        vs = []
        rule()
        vs.append(self.val)
        if self.failed:
            return
        self._star(rule, vs)

    def _pop(self, name):
        actual_name, _ = self.scopes.pop()
        assert name == actual_name

    def _push(self, name):
        self.scopes.append((name, {}))

    def _range(self, i, j):
        p = self.pos
        if p != self.end and ord(i) <= ord(self.msg[p]) <= ord(j):
            self._succeed(self.msg[p], self.pos + 1)
        else:
            self._fail()

    def _rewind(self, newpos):
        self._succeed(None, newpos)

    def _seq(self, rules):
        for rule in rules:
            rule()
            if self.failed:
                return

    def _set(self, var, val):
        self.scopes[-1][1][var] = val

    def _star(self, rule, vs=None):
        vs = vs or []
        while True:
            p = self.pos
            rule()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _str(self, s):
        for ch in s:
            self._ch(ch)
            if self.failed:
                return
        self.val = s

    def _succeed(self, v, newpos=None):
        self.val = v
        self.failed = False
        if newpos is not None:
            self.pos = newpos

    def _unicat(self, cat):
        p = self.pos
        if p < self.end and unicodedata.category(self.msg[p]) == cat:
            self._succeed(self.msg[p], self.pos + 1)
        else:
            self._fail()

    def _utoi(self, s):
        return ord(s)

    def _xtoi(self, s):
        return int(s, base=16)

    def _xtou(self, s):
        return chr(int(s, base=16))
"""
