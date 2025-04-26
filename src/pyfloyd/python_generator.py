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

# pylint: disable=too-many-lines

import re
import shlex
import sys
from typing import Dict, List

from pyfloyd.analyzer import Grammar
from pyfloyd.formatter import flatten, Comma, Saw, Tree
from pyfloyd.generator import Generator, GeneratorOptions, FormatObj
from pyfloyd.version import __version__
from pyfloyd import string_literal as lit


class PythonGenerator(Generator):
    def __init__(self, grammar: Grammar, options: GeneratorOptions):
        super().__init__(grammar, options)
        self._builtin_methods = self._load_builtin_methods()
        self._methods: Dict[str, List[str]] = {}
        self._operators: Dict[str, str] = {}
        self._map = {
            'end': '',
            'false': 'False',
            'Infinity': "float('inf')",
            'NaN': "float('NaN')",
            'not': 'not ',
            'null': 'None',
            'true': 'True',
        }

        self._end_stmt = ''


    def _gen_rules(self) -> None:
        for rule, node in self._grammar.rules.items():
            self._current_rule = self._base_rule_name(rule)
            self._methods[rule] = self._gen_expr(node)
            self._current_rule = None

    def _gen_text(self) -> str:
        imports = ''
        if self._options.main:
            imports += 'import argparse\n'
        if self._options.main:
            imports += 'import json\n'
            imports += 'import os\n'
        if self._grammar.re_needed:
            imports += 'import re\n'
        if self._options.main:
            imports += 'import sys\n'
        imports += 'from typing import Any, Dict, NamedTuple, Optional\n'
        if self._unicodedata_needed:
            imports += 'import unicodedata\n'

        version = __version__
        args = shlex.join(sys.argv[1:])
        if self._options.main:
            text = _MAIN_HEADER.format(
                version=version, args=args, imports=imports
            )
        else:
            text = _DEFAULT_HEADER.format(
                version=version, args=args, imports=imports
            )

        if self._exception_needed:
            text += _PARSING_RUNTIME_EXCEPTION

        if self._grammar.operators:
            text += _OPERATOR_CLASS
        if self._grammar.externs:
            externs = '{\n            '
            externs += '\n            '.join(
                f"'{k}': {v}," for k, v in self._grammar.externs.items()
            )
            externs += '\n        }'
        else:
            externs = '{}'
        text += _CLASS.format(externs=externs)

        text += self._state()
        text += '\n'

        if self._exception_needed:
            text += _PARSE_WITH_EXCEPTION.format(
                starting_rule=self._grammar.starting_rule
            )
        else:
            text += _PARSE.format(starting_rule=self._grammar.starting_rule)

        text += self._gen_methods()
        if self._options.main:
            text += _MAIN_FOOTER
        else:
            text += _DEFAULT_FOOTER
        return text

    def _state(self) -> str:
        text = ''
        if self._options.memoize:
            text += '        self._cache = {}\n'
        if self._grammar.leftrec_needed or self._grammar.operator_needed:
            text += '        self._seeds = {}\n'
        if self._grammar.leftrec_needed:
            text += '        self._blocked = set()\n'
        if self._grammar.re_needed:
            text += '        self._regexps = {}\n'
        if self._grammar.outer_scope_rules:
            text += '        self._scopes = []\n'
            self._needed_methods.add('lookup')
        if self._grammar.operator_needed:
            text += self._operator_state()
            text += '\n'

        return text

    def _operator_state(self) -> str:
        text = '        self._operators = {}\n'
        for rule, o in self._grammar.operators.items():
            text += '        o = _OperatorState()\n'
            text += '        o.prec_ops = {\n'
            for prec in sorted(o.prec_ops):
                text += '            %d: [' % prec
                text += ', '.join("'%s'" % op for op in o.prec_ops[prec])
                text += '],\n'
            text += '        }\n'
            text += '        o.precs = sorted(o.prec_ops, reverse=True)\n'
            text += '        o.rassoc = set(['
            text += ', '.join("'%s'" % op for op in o.rassoc)
            text += '])\n'
            text += '        o.choices = {\n'
            for op in o.choices:
                text += "            '%s': self._%s,\n" % (op, o.choices[op])
            text += '        }\n'
            text += "        self._operators['%s'] = o\n" % rule
        return text

    def _load_builtin_methods(self) -> Dict[str, str]:
        blocks = _BUILTIN_METHODS.split('\n    def ')
        blocks[0] = blocks[0][8:]
        builtins = {}
        for block in blocks:
            name = block[1 : block.find('(')]
            text = '    def ' + block
            builtins[name] = text
        return builtins

    def _gen_methods(self) -> str:
        text = ''
        for rule, method_body in self._methods.items():
            text += self._gen_method_text(rule, method_body)
        text += '\n'

        if self._grammar.needed_builtin_rules:
            text += '\n'.join(
                self._builtin_methods[f'r_{name}']
                for name in sorted(self._grammar.needed_builtin_rules)
            )
            text += '\n'

        text += '\n'.join(
            self._builtin_methods[name]
            for name in sorted(self._needed_methods)
        )

        if self._grammar.needed_builtin_functions:
            text += '\n'
            text += '\n'.join(
                self._builtin_methods[f'fn_{name}']
                for name in sorted(self._grammar.needed_builtin_functions)
            )
        return text

    def _gen_method_text(self, method_name, method_body) -> str:
        text = '\n'
        text += '    def _%s(self):\n' % method_name
        for line in method_body:
            text += f'        {line}\n'
        return text

    def _thisvar(self, v):
        return 'self._' + v

    def _rulename(self, r):
        return 'self._' + r

    def _extern(self, v):
        return "self._externs['" + v + "']"

    def _invoke(self, fn, *args):
        return 'self._' + fn + '(' + ', '.join(args) + ')'

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _ty_action(self, node) -> List[str]:
        obj = self._gen_expr(node[2][0])
        return flatten(Saw('self._succeed(', obj, ')'))

    def _ty_apply(self, node) -> List[str]:
        if self._options.memoize and node[1].startswith('r_'):
            name = node[1][2:]
            if (
                name not in self._grammar.operators
                and name not in self._grammar.leftrec_rules
            ):
                return [
                    self._invoke('memoize', f"'{node[1]}'",
                                 self._rulename(node[1]))
                ]

        return [self._invoke(node[1])]

    def _ty_choice(self, node) -> List[str]:
        lines = ['p = self._pos']
        for subnode in node[2][:-1]:
            lines.extend(self._gen_expr(subnode))
            lines.append('if not self._failed:')
            lines.append('    return')
            lines.append('self._rewind(p)')
        lines.extend(self._gen_expr(node[2][-1]))
        return lines

    def _ty_count(self, node) -> List[str]:
        lines = [
            'vs = []',
            'i = 0',
            f'cmin, cmax = {node[1]}',
            'while i < cmax:',
        ]
        lines.extend(['    ' + line for line in self._gen_expr(node[2][0])])
        lines.extend(
            [
                '    if self._failed:',
                '        if i >= cmin:',
                '            self._succeed(vs)',
                '            return',
                '        return',
                '    vs.append(self._val)',
                '    i += 1',
                'self._succeed(vs)',
            ]
        )
        return lines

    def _ty_empty(self, node) -> List[str]:
        del node
        return [self._invoke('succeed', self._map['null']) + self._map['end']]

    def _ty_ends_in(self, node) -> List[str]:
        sublines = self._gen_expr(node[2][0])
        lines = [
            'while True:',
        ] + ['    ' + line for line in sublines]
        if self._can_fail(node[2][0], True):
            lines.extend(['    if not self._failed:', '        break'])
        lines.extend(
            [
                '    self._r_any()',
                '    if self._failed:',
                '        break',
            ]
        )
        return lines

    def _ty_equals(self, node) -> List[str]:
        arg = self._gen_expr(node[2][0])
        return [f'self._str({flatten(arg)[0]})']

    def _ty_label(self, node) -> List[str]:
        lines = self._gen_expr(node[2][0])
        if self._can_fail(node[2][0], True):
            lines.extend(['if self._failed:', '    return'])
        if self._current_rule in self._grammar.outer_scope_rules:
            lines.extend([f"self._scopes[-1]['{node[1]}'] = self._val"])
        else:
            lines.extend(
                [
                    f'{self._varname(node[1])} = self._val',
                ]
            )
        return lines

    def _ty_leftrec(self, node) -> List[str]:
        left_assoc = self._grammar.assoc.get(node[1], 'left') == 'left'
        lines = [
            f'self._leftrec(self._{node[2][0][1]}, '
            + f"'{node[1]}', {str(left_assoc)})"
        ]
        return lines

    def _ty_lit(self, node) -> List[str]:
        expr = lit.encode(node[1])
        if len(node[1]) == 1:
            method = 'ch'
        else:
            method = 'str'
        return [f'self._{method}({expr})']

    def _ty_not(self, node) -> List[str]:
        sublines = self._gen_expr(node[2][0])
        lines = (
            [
                'p = self._pos',
                'errpos = self._errpos',
            ]
            + sublines
            + [
                'if self._failed:',
                '    self._succeed(None, p)',
                'else:',
                '    self._rewind(p)',
                '    self._errpos = errpos',
                '    self._fail()',
            ]
        )
        return lines

    def _ty_not_one(self, node) -> List[str]:
        sublines = self._gen_expr(['not', None, node[2]])
        return sublines + ['if not self._failed:', '    self._r_any()']

    def _ty_operator(self, node) -> List[str]:
        self._needed_methods.add('operator')
        # Operator nodes have no children, but subrules for each arm
        # of the expression cluster have been defined and are referenced
        # from self._grammar.operators[node[1]].choices.
        assert node[2] == []
        return [f"self._operator(f'{node[1]}')"]

    def _ty_opt(self, node) -> List[str]:
        sublines = self._gen_expr(node[2][0])
        lines = (
            [
                'p = self._pos',
            ]
            + sublines
            + [
                'if self._failed:',
                '    self._succeed([], p)',
                'else:',
                '    self._succeed([self._val])',
            ]
        )
        return lines

    def _ty_paren(self, node) -> List[str]:
        return self._gen_expr(node[2][0])

    def _ty_plus(self, node) -> List[str]:
        sublines = self._gen_expr(node[2][0])
        lines = (
            ['vs = []']
            + sublines
            + [
                'if self._failed:',
                '    return',
                'vs.append(self._val)',
                'while True:',
                '    p = self._pos',
            ]
            + ['    ' + line for line in sublines]
            + [
                '    if self._failed or self._pos == p:',
                '        self._rewind(p)',
                '        break',
                '    vs.append(self._val)',
                'self._succeed(vs)',
            ]
        )

        return lines

    def _ty_pred(self, node) -> List[str]:
        arg = self._gen_expr(node[2][0])
        # TODO: Figure out how to statically analyze predicates to
        # catch ones that don't return booleans, so that we don't need
        # the _ParsingRuntimeError exception
        self._exception_needed = True
        return [
            'v = ' + flatten(arg)[0],
            'if v is True:',
            '    self._succeed(v)',
            'elif v is False:',
            '    self._fail()',
            'else:',
            "    raise _ParsingRuntimeError('Bad predicate value')",
        ]

    def _ty_range(self, node) -> List[str]:
        return [
            'self._range(%s, %s)'
            % (lit.encode(node[1][0]), lit.encode(node[1][1]))
        ]

    def _ty_regexp(self, node) -> List[str]:
        return [
            f'p = {lit.encode(node[1])}',
            'if p not in self._regexps:',
            '    self._regexps[p] = re.compile(p)',
            'm = self._regexps[p].match(self._text, self._pos)',
            'if m:',
            '    self._succeed(m.group(0), m.end())',
            '    return',
            'self._fail()',
        ]

    def _ty_run(self, node) -> List[str]:
        sublines = self._gen_expr(node[2][0])
        lines = ['start = self._pos'] + sublines
        if self._can_fail(node[2][0], True):
            lines.extend(['if self._failed:', '    return'])
        lines.extend(
            [
                'end = self._pos',
                'self._val = self._text[start:end]',
            ]
        )
        return lines

    def _ty_scope(self, node) -> List[str]:
        return (
            [
                'self._scopes.append({})',
            ]
            + self._gen_expr(node[2][0])
            + [
                'self._scopes.pop()',
            ]
        )

    def _ty_set(self, node) -> List[str]:
        new_node = ['regexp', '[' + node[1] + ']', []]
        return self._ty_regexp(new_node)

    def _ty_seq(self, node) -> List[str]:
        lines = self._gen_expr(node[2][0])
        if self._can_fail(node[2][0], inline=True):
            lines.extend(['if self._failed:', '    return'])
        for subnode in node[2][1:-1]:
            lines.extend(self._gen_expr(subnode))
            if self._can_fail(subnode, inline=True):
                lines.extend(['if self._failed:', '    return'])
        lines.extend(self._gen_expr(node[2][-1]))
        return lines

    def _ty_star(self, node) -> List[str]:
        sublines = self._gen_expr(node[2][0])
        lines = (
            [
                'vs = []',
                'while True:',
                '    p = self._pos',
            ]
            + ['    ' + line for line in sublines]
            + [
                '    if self._failed or self._pos == p:',
                '        self._rewind(p)',
                '        break',
                '    vs.append(self._val)',
                'self._succeed(vs)',
            ]
        )
        return lines

    def _ty_unicat(self, node) -> List[str]:
        return ['self._unicat(%s)' % lit.encode(node[1])]


_DEFAULT_HEADER = """\
# Generated by pyfloyd version {version}
#    https://github.com/dpranke/pyfloyd
#    `pyfloyd {args}`

{imports}

Externs = Optional[Dict[str, Any]]

# pylint: disable=too-many-lines


"""


_DEFAULT_FOOTER = ''


_MAIN_HEADER = """\
#!/usr/bin/env python3
#
# Generated by pyfloyd version {version}
#    https://github.com/dpranke/pyfloyd
#    `pyfloyd {args}`

{imports}
import json
import re
from typing import Any, Optional, Dict

Externs = Optional[Dict[str, Any]]

# pylint: disable=too-many-lines


def main(
    argv=sys.argv[1:],
    stdin=sys.stdin,
    stdout=sys.stdout,
    stderr=sys.stderr,
    exists=os.path.exists,
    opener=open,
) -> int:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        '-D',
        '--define',
        action='append',
        metavar='var=val',
        default=[],
        help='define an external var=value (may use multiple times)'
    )
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

    externs = {{}}
    for d in args.define:
        k, v = d.split('=', 1)
        externs[k] = json.loads(v)

    msg = fp.read()
    result = parse(msg, path, externs)
    if result.err:
        print(result.err, file=stderr)
        return 1
    print(json.dumps(result.val, indent=2), file=stdout)
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

_OPERATOR_CLASS = """\
class _OperatorState:
    def __init__(self):
        self.current_depth = 0
        self.current_prec = 0
        self.prec_ops = {}
        self.precs = []
        self.rassoc = set()
        self.choices = {}


"""

_CLASS = """\
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


def parse(
    text: str, path: str = '<string>', externs: Externs = None
) -> Result:
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
    return _Parser(text, path).parse(externs)


class _Parser:
    def __init__(self, text, path):
        self._text = text
        self._end = len(self._text)
        self._errpos = 0
        self._externs = {externs}
        self._failed = False
        self._path = path
        self._pos = 0
        self._val = None
"""


_PARSE = """\
    def parse(self, externs: Externs = None):
        if externs:
            for k, v in externs.items():
                self._externs[k] = v

        self._r_{starting_rule}()
        if self._failed:
            return Result(None, self._error(), self._errpos)
        return Result(self._val, None, self._pos)
"""


_PARSE_WITH_EXCEPTION = """\
    def parse(self, externs: Externs = None):
        errors = ''
        if externs:
            for k, v in externs.items():
                if k in self._externs:
                    self._externs[k] = v
                else:
                    errors += f'Unexpected extern "{{k}}"\\n'
        if errors:
            return Result(None, errors, 0)
        try:
            self._r_{starting_rule}()
            if self._failed:
                return Result(None, self._error(), self._errpos)
            return Result(self._val, None, self._pos)
        except _ParsingRuntimeError as e:  # pragma: no cover
            lineno, _ = self._offsets(self._errpos)
            return Result(
                None,
                self._path + ':' + str(lineno) + ' ' + str(e),
                self._errpos,
            )
"""


_BUILTIN_METHODS = """\
    def _r_any(self):
        if self._pos < self._end:
            self._succeed(self._text[self._pos], self._pos + 1)
        else:
            self._fail()

    def _r_end(self):
        if self._pos == self._end:
            self._succeed(None)
        else:
            self._fail()

    def _ch(self, ch):
        p = self._pos
        if p < self._end and self._text[p] == ch:
            self._succeed(ch, self._pos + 1)
        else:
            self._fail()

    def _offsets(self, pos):
        lineno = 1
        colno = 1
        for i in range(pos):
            if self._text[i] == '\\n':
                lineno += 1
                colno = 1
            else:
                colno += 1
        return lineno, colno

    def _error(self):
        lineno, colno = self._offsets(self._errpos)
        if self._errpos == len(self._text):
            thing = 'end of input'
        else:
            thing = repr(self._text[self._errpos]).replace("'", '"')
        return '%s:%d Unexpected %s at column %d' % (
            self._path,
            lineno,
            thing,
            colno,
        )

    def _fail(self):
        self._val = None
        self._failed = True
        self._errpos = max(self._errpos, self._pos)

    def _leftrec(self, rule, rule_name, left_assoc):
        pos = self._pos
        key = (rule_name, pos)
        seed = self._seeds.get(key)
        if seed:
            self._val, self._failed, self._pos = seed
            return
        if rule_name in self._blocked:
            self._val = None
            self._failed = True
            return
        current = (None, True, self._pos)
        self._seeds[key] = current
        if left_assoc:
            self._blocked.add(rule_name)
        while True:
            rule()
            if self._pos > current[2]:
                current = (self._val, self._failed, self._pos)
                self._seeds[key] = current
                self._pos = pos
            else:
                del self._seeds[key]
                self._val, self._failed, self._pos = current
                if left_assoc:
                    self._blocked.remove(rule_name)
                return

    def _lookup(self, var):
        l = len(self._scopes) - 1
        while l >= 0:
            if var in self._scopes[l]:
                return self._scopes[l][var]
            l -= 1
        if var in self._externs:
            return self._externs[var]
        assert False, f'unknown var {var}'

    def _memoize(self, rule_name, fn):
        p = self._pos
        r = self._cache.setdefault(p, {}).get(rule_name)
        if r:
            self._val, self._failed, self._pos = r
            return
        fn()
        self._cache[p][rule_name] = (self._val, self._failed, self._pos)

    def _operator(self, rule_name):
        o = self._operators[rule_name]
        pos = self._pos
        key = (rule_name, self._pos)
        seed = self._seeds.get(key)
        if seed:
            self._val, self._failed, self._pos = seed
            return
        o.current_depth += 1
        current = (None, True, self._pos)
        self._seeds[key] = current
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
                if not self._failed and self._pos > pos:
                    current = (self._val, self._failed, self._pos)
                    self._seeds[key] = current
                    repeat = True
                    break
                self._rewind(pos)
            if not repeat:
                i += 1

        del self._seeds[key]
        o.current_depth -= 1
        if o.current_depth == 0:
            o.current_prec = 0
        self._val, self._failed, self._pos = current

    def _range(self, i, j):
        p = self._pos
        if p != self._end and ord(i) <= ord(self._text[p]) <= ord(j):
            self._succeed(self._text[p], self._pos + 1)
        else:
            self._fail()

    def _rewind(self, newpos):
        self._succeed(None, newpos)

    def _str(self, s):
        for ch in s:
            self._ch(ch)
            if self._failed:
                return
        self._val = s

    def _succeed(self, v, newpos=None):
        self._val = v
        self._failed = False
        if newpos is not None:
            self._pos = newpos

    def _unicat(self, cat):
        p = self._pos
        if p < self._end and unicodedata.category(self._text[p]) == cat:
            self._succeed(self._text[p], self._pos + 1)
        else:
            self._fail()

    def _fn_atof(self, s):
        if '.' in s or 'e' in s or 'E' in s:
            return float(s)
        return int(s)

    def _fn_atoi(self, a, base):
        return int(a, base)

    def _fn_atou(self, a, base):
        return chr(int(a, base))

    def _fn_cat(self, strs):
        return ''.join(strs)

    def _fn_concat(self, xs, ys):
        return xs + ys

    def _fn_cons(self, hd, tl):
        return [hd] + tl

    def _fn_dedent(self, s):
        return s

    def _fn_dict(self, pairs):
        return dict(pairs)

    def _fn_itou(self, n):
        return chr(n)

    def _fn_join(self, s, vs):
        return s.join(vs)

    def _fn_otou(self, s):
        return chr(int(s, base=8))

    def _fn_scat(self, hd, tl):
        return self._fn_cat(self._fn_cons(hd, tl))

    def _fn_scons(self, hd, tl):
        return [hd] + tl

    def _fn_strcat(self, a, b):
        return a + b

    def _fn_unicode_lookup(self, s):
        return unicodedata.unicode_lookup(s)

    def _fn_utoi(self, s):
        return ord(s)

    def _fn_xtoi(self, s):
        return int(s, base=16)

    def _fn_xtou(self, s):
        return chr(int(s, base=16))
"""
