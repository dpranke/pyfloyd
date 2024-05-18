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

import enum

from floyd import string_literal


Whitespace = enum.Enum(
    'Whitespace',
    [
        'Indent',
        'Newline',
        'OptionalIndent',
        'OptionalUnindent',
        'SpaceOrNewline',
        'SpaceOrIndent',
        'Unindent',
    ],
)

IN = Whitespace.Indent
NL = Whitespace.Newline
OI = Whitespace.OptionalIndent
OU = Whitespace.OptionalUnindent
SN = Whitespace.SpaceOrNewline
UN = Whitespace.Unindent


_DEFAULT_HEADER = '{unicodedata_import}'


_DEFAULT_FOOTER = ''


_MAIN_HEADER = """\
#!/usr/bin/env python

import argparse
import json
import os
import sys
{unicodedata_import}

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
    print(json.dumps(obj, indent=2))
    return 0

"""


_MAIN_FOOTER = """\

if __name__ == '__main__':
    sys.exit(main())
"""


_PARSING_RUNTIME_EXCEPTION = """\
class _ParsingRuntimeError(Exception):
    pass
"""

_CLASS = """\
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


_PARSE = """\
    def parse(self):
        self._{starting_rule}_()
        if self.failed:
            return None, self._err_str(), self.errpos
        return self.val, None, self.pos
"""


_PARSE_WITH_EXCEPTION = """\
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


_BUILTINS = """\
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
          return float(str)

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


class Compiler:
    def __init__(self, grammar, classname, main_wanted=True, memoize=True):
        self._grammar = grammar
        self._classname = classname
        self._depth = 0
        self._main_wanted = main_wanted
        self._memoize = memoize
        self._needed = set()
        self._methods = {}
        self._method_lines = []
        self._exception_needed = False
        self._unicodedata_needed = False

    def compile(self):
        for rule, node in self._grammar.rules.items():
            self._compile(node, rule, top_level=True)

        if self._unicodedata_needed:
            unicodedata_import = 'import unicodedata\n'
        else:
            unicodedata_import = ''

        # These methods are always needed.
        self._needed.update(
            {
                'err_offsets',
                'err_str',
                'fail',
                'rewind',
                'succeed',
            }
        )

        if self._main_wanted:
            text = _MAIN_HEADER.format(
                classname=self._classname,
                unicodedata_import=unicodedata_import,
            )
        else:
            text = _DEFAULT_HEADER.format(
                unicodedata_import=unicodedata_import
            )

        if self._exception_needed:
            text += _PARSING_RUNTIME_EXCEPTION

        text += _CLASS.format(classname=self._classname)

        if self._memoize:
            text += '        self.cache = {}\n'
        if 'bind' in self._needed:
            text += '        self.scopes = []\n'
            self._needed.update(
                {
                    'get',
                    'push',
                    'pop',
                    'set',
                }
            )
        if 'leftrec' in self._needed:
            text += '        self.seeds = {}\n'
            text += '        self.blocked = set()\n'
        text += '\n'

        if self._exception_needed:
            text += _PARSE_WITH_EXCEPTION.format(
                starting_rule=self._grammar.starting_rule
            )
        else:
            text += _PARSE.format(starting_rule=self._grammar.starting_rule)

        methods = set()
        for rule in self._grammar.rules.keys():
            methods.add(rule)
            text += self._method_text(
                rule, self._methods[rule], memoize=self._memoize
            )

            # Do not memoize the internal rules; it's not clear if that'd
            # ever be useful.
            names = [
                m
                for m in self._methods
                if m.startswith(rule + '_') and m not in methods
            ]
            for name in sorted(names):
                methods.add(name)
                text += self._method_text(
                    name, self._methods[name], memoize=False
                )
        text += '\n'

        builtins = self._load_builtins()
        text += '\n'.join(builtins[name] for name in sorted(self._needed))

        if self._main_wanted:
            text += _MAIN_FOOTER
        else:
            text += _DEFAULT_FOOTER
        return text, None

    def _load_builtins(self):
        blocks = _BUILTINS.split('\n    def ')
        blocks[0] = blocks[0][8:]
        builtins = {}
        for block in blocks:
            name = block[1 : block.find('(')]
            if name == 'end_':
                name = 'end'
            if name == 'any_':
                name = 'any'
            text = '    def ' + block
            builtins[name] = text
        return builtins

    def _method_text(self, name, lines, memoize):
        text = '\n'
        text += '    def _%s_(self):\n' % name
        if memoize:
            text += '        r = self.cache.get(("%s", self.pos))\n' % name
            text += '        if r is not None:\n'
            text += '            self.val, self.failed, self.pos = r\n'
            text += '            return\n'
            text += '        pos = self.pos\n'
        for line in lines:
            text += '        %s\n' % line
        if memoize:
            text += '        self.cache[("%s", pos)] = (' % name
            text += 'self.val, self.failed, self.pos)\n'
        return text

    def _compile(self, node, rule, sub_type='', index=0, top_level=False):
        assert node
        assert not self._method_lines
        # TODO: Figure out how to handle inlining methods more consistently
        # so that we don't have the special-casing logic here.
        if node[0] == 'apply':
            # Unknown rules were caught in analysis so if the rule isn't
            # one of the ones in the grammar it must be a built-in one.
            if node[1] not in self._grammar.rules:
                self._needed.add(node[1])
            return 'self._%s_' % node[1]
        if node[0] == 'lit' and not top_level:
            expr = string_literal.encode(node[1])
            if len(node[1]) == 1:
                self._needed.add('ch')
                return 'lambda: self._ch(%s)' % (expr,)
            self._needed.add('ch')
            self._needed.add('str')
            return 'lambda: self._str(%s)' % (expr,)
        if sub_type:
            sub_rule = '%s__%s%d' % (rule, sub_type, index)
        else:
            sub_rule = rule
        fn = getattr(self, '_%s_' % node[0])
        if top_level and node[0] in ('seq', 'choice'):
            fn(sub_rule, node, top_level)
        else:
            fn(sub_rule, node)

        assert sub_rule not in self._methods
        self._methods[sub_rule] = self._method_lines
        self._method_lines = []
        return 'self._%s_' % sub_rule

    def _fits(self, line):
        return len(line) < 72

    def _eval_rule(self, rule, node):
        fn = getattr(self, '_' + node[0] + '_')
        return fn(rule, node)

    def _ext(self, *lines):
        self._method_lines.extend(lines)

    def _indent(self, s):
        return self._depth * '    ' + s

    def _flatten(self, obj):
        lines = self._flatten_rec(obj, 0, self._max_depth(obj) + 1)
        for line in lines[:-1]:
            self._ext(line.rstrip())

        # TODO: Figure out how to handle blank lines at the end of a method
        # better. There will be a blank line if obj[-1] == UN.
        if lines[-1].rstrip():
            self._ext(lines[-1].rstrip())

    def _flatten_rec(self, obj, current_depth, max_depth):
        for i in range(current_depth, max_depth):
            lines = []
            s = ''
            try:
                for el in obj:
                    if isinstance(el, str):
                        s += el
                    elif el == IN:
                        lines.append(self._indent(s))
                        self._depth += 1
                        s = ''
                    elif el == NL:
                        lines.append(self._indent(s))
                        s = ''
                    elif el == OI:
                        if i > 0:
                            lines.append(self._indent(s))
                            self._depth += 1
                            s = ''
                    elif el == OU:
                        if i > 0:
                            lines.append(self._indent(s))
                            self._depth -= 1
                            s = ''
                    elif el == SN:
                        if i == 0:
                            s += ' '
                        else:
                            lines.append(self._indent(s))
                            s = ''
                    elif el == UN:
                        lines.append(self._indent(s))
                        self._depth -= 1
                        s = ''
                    else:  # el must be an obj
                        new_lines = self._flatten_rec(el, max(i - 1, 0), max(i, 1))
                        s += new_lines[0]
                        if len(new_lines) > 1:
                            lines.append(s)
                            lines.extend(new_lines[1:-1])
                            s = new_lines[-1]

                lines.append(s)
                if all(self._fits(line) for line in lines):
                    break
            except TypeError as e:
                import pdb; pdb.set_trace()
                pass
        return lines

    def _max_depth(self, obj):
        if isinstance(obj, list):
            return max(self._max_depth(el) + 1 for el in obj)
        return 1

    def _has_labels(self, node):
        if node and node[0] in ('label', 'll_var'):
            return True
        for n in node:
            if isinstance(n, list) and self._has_labels(n):
                return True
        return False

    def _chain(self, name, args):
        obj = ['self._', name, '(', IN, '[', IN]
        for i in range(len(args)):  # pylint: disable=consider-using-enumerate
            obj.append(args[i])
            if i < len(args) - 1:
                obj.append(',')
                obj.append(NL)
            else:
                obj.append(',')
                obj.append(UN)
        obj.extend([']', UN, ')'])
        self._flatten(obj)

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _choice_(self, rule, node, top_level=False):
        self._needed.add('choose')
        sub_rules = [
            self._compile(sub_node, rule, 'c', i, top_level)
            for i, sub_node in enumerate(node[2])
        ]
        self._chain('choose', sub_rules)

    def _seq_(self, rule, node, top_level=False):
        self._needed.add('seq')
        sub_rules = [
            self._compile(sub_node, rule, 's', i)
            for i, sub_node in enumerate(node[2])
        ]
        needs_scope = top_level and self._has_labels(node)
        if needs_scope:
            self._flatten(["self._push('", rule, "')"])
        self._chain('seq', sub_rules)
        if needs_scope:
            self._flatten(["self._pop('", rule, "')"])

    def _lit_(self, rule, node):
        del rule
        expr = string_literal.encode(node[1])
        if len(node[1]) == 1:
            method = 'ch'
        else:
            method = 'str'
            self._needed.add('ch')
        self._needed.add(method)
        self._flatten(['self._', method, '(', expr, ')'])

    def _label_(self, rule, node):
        self._needed.add('bind')
        sub_rule = self._compile(node[2][0], rule + '_l')
        self._flatten(
            [
                'self._bind(',
                sub_rule,
                ', ',
                string_literal.encode(node[1]),
                ')',
            ]
        )

    def _leftrec_(self, rule, node):
        sub_rule = self._compile(node[2][0], rule + '_l')
        self._needed.add('leftrec')
        left_assoc = self._grammar.assoc.get(node[1], 'left') == 'left'
        needs_scope = self._has_labels(node)
        if needs_scope:
            self._flatten(["self._push('", rule, "')"])
        self._flatten(
            ['self._leftrec(', OI, sub_rule, ',', "'", node[1], "'", 
             ',', str(left_assoc), OU, ')']
        )
        if needs_scope:
            self._flatten(["self._pop('", rule, "')"])

    def _action_(self, rule, node):
        self._depth = 0
        obj = self._eval_rule(rule, node[2][0])
        self._flatten(['self._succeed(', OI, obj, OU, ')'])

    def _empty_(self, rule, node):
        del rule
        del node
        self._flatten(['self._succeed(None)'])

    def _not_(self, rule, node):
        self._needed.add('not')
        sub_rule = self._compile(node[2][0], rule + '_n')
        self._flatten(['self._not(', sub_rule, ')'])

    def _paren_(self, rule, node):
        sub_rule = self._compile(node[2][0], rule + '_g')
        if sub_rule.startswith('lambda:'):
            self._flatten([sub_rule[8:]])
        else:
            self._flatten(['(', sub_rule, ')()'])

    def _post_(self, rule, node):
        sub_rule = self._compile(node[2][0], rule + '_p')
        if node[1] == '?':
            method = 'opt'
        elif node[1] == '+':
            method = 'plus'
            self._needed.add('star')
        else:
            assert node[1] == '*'
            method = 'star'
        self._needed.add(method)
        self._flatten(['self._', method, '(', OI, sub_rule, OU, ')'])

    def _pred_(self, rule, node):
        obj = self._eval_rule(rule, node[2][0])
        # TODO: Figure out how to statically analyze predicates to
        # catch ones that don't return booleans, so that we don't need
        # the _ParsingRuntimeError exception
        self._exception_needed = True
        self._flatten(
            [
                'v = ',
                obj,
                NL,
                'if v is True:',
                IN,
                'self._succeed(v)',
                UN,
                'elif v is False:',
                IN,
                'self._fail()',
                UN,
                'else:',
                IN,
                "raise _ParsingRuntimeError('Bad predicate value')",
                UN,
            ]
        )

    def _range_(self, rule, node):
        del rule
        self._needed.add('range')
        self._flatten(
            [
                'self._range(',
                string_literal.encode(node[2][0][1]),
                ', ',
                string_literal.encode(node[2][1][1]),
                ')',
            ]
        )

    def _unicat_(self, rule, node):
        del rule
        self._unicodedata_needed = True
        self._needed.add('unicat')
        self._flatten(['self._unicat(', string_literal.encode(node[1]), ')'])

    #
    # Handlers for the host nodes in the AST
    #

    def _ll_arr_(self, rule, node):
        line = ['[', OI]
        if len(node[2]):
            line.append(self._eval_rule(rule, node[2][0]))
            for e in node[2][1:]:
                line.extend([',', SN, self._eval_rule(rule, e)])
        line.extend([OU, ']'])
        return line

    def _ll_call_(self, rule, node):
        line = ['(', OI]

        # There are no built-in functions that take no arguments, so make
        # sure we're not being called that way.
        assert len(node[2]) != 0

        line.append(self._eval_rule(rule, node[2][0]))
        for e in node[2][1:]:
            line.extend([',', SN, self._eval_rule(rule, e)])
        line.extend([OU, ')'])
        return line

    def _ll_getitem_(self, rule, node):
        return ['['] + self._eval_rule(rule, node[2][0]) + [']']

    def _ll_lit_(self, rule, node):
        del rule
        return [string_literal.encode(node[1])]

    def _ll_minus_(self, rule, node):
        return (
            self._eval_rule(rule, node[2][0])
            + [SN, '- ']
            + self._eval_rule(rule, node[2][1])
        )

    def _ll_num_(self, rule, node):
        del rule
        return [node[1]]

    def _ll_paren_(self, rule, node):
        return self._eval_rule(rule, node[2][0])

    def _ll_plus_(self, rule, node):
        return (
            self._eval_rule(rule, node[2][0])
            + [SN, '+ ']
            + self._eval_rule(rule, node[2][1])
        )

    def _ll_qual_(self, rule, node):
        if node[2][1][0] == 'll_call':
            self._needed.add(node[2][0][1])
            v = ['self._%s' % node[2][0][1]]
        else:
            v = self._eval_rule(rule, node[2][0])
        for p in node[2][1:]:
            v += self._eval_rule(rule, p)
        return [v]

    def _ll_var_(self, rule, node):
        del rule
        return ["self._get('%s')" % node[1]]

    def _ll_const_(self, rule, node):
        del rule
        if node[1] == 'false':
            return 'False'
        if node[1] == 'null':
            return 'None'
        if node[1] == 'true':
            return 'True'
        if node[1] == 'Infinity':
            return "float('inf')"
        assert node[1] == 'NaN'
        return "float('NaN')"
