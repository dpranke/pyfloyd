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

from typing import Dict, List, Union

from floyd.analyzer import Grammar
from floyd.formatter import flatten, Comma, Saw, Tree
from floyd.generator import Generator, GeneratorOptions
from floyd import string_literal as lit


_FormatObj = Union[Comma, Tree, Saw, str]


class PythonGenerator(Generator):
    def __init__(self, grammar: Grammar, options: GeneratorOptions):
        super().__init__(grammar, options)
        self._builtin_methods = self._load_builtin_methods()
        self._builtin_functions = self._load_builtin_functions()
        self._exception_needed = False
        self._methods: Dict[str, List[str]] = {}
        self._operators: Dict[str, str] = {}
        self._unicodedata_needed = (
            grammar.unicat_needed
            or 'is_unicat' in grammar.needed_builtin_functions
        )

        # These methods are pretty much always needed.
        self._needed_methods = set(
            {
                'err_offsets',
                'err_str',
                'fail',
                'rewind',
                'succeed',
            }
        )
        if grammar.ch_needed:
            self._needed_methods.add('ch')
        if grammar.leftrec_needed:
            self._needed_methods.add('leftrec')
        if grammar.operator_needed:
            self._needed_methods.add('operator')
        if grammar.range_needed:
            self._needed_methods.add('range')
        if grammar.str_needed:
            self._needed_methods.add('str')
        if grammar.unicat_needed:
            self._needed_methods.add('unicat')

    def generate(self) -> str:
        self._gen_rules()
        return self._gen_text()

    def _gen_rules(self) -> None:
        for rule, node in self.grammar.rules.items():
            self._methods[rule] = self._gen(node)

    def _gen_text(self) -> str:
        unicodedata_import = ''
        if self._unicodedata_needed:
            unicodedata_import = 'import unicodedata\n\n'

        if self.options.main:
            text = _MAIN_HEADER.format(
                unicodedata_import=unicodedata_import,
            )
        else:
            text = _DEFAULT_HEADER.format(
                unicodedata_import=unicodedata_import
            )

        if self._exception_needed:
            text += _PARSING_RUNTIME_EXCEPTION

        if self.grammar.operators:
            text += _OPERATOR_CLASS

        text += _CLASS

        text += self._state()
        text += '\n'

        if self._exception_needed:
            text += _PARSE_WITH_EXCEPTION.format(
                starting_rule=self.grammar.starting_rule
            )
        else:
            text += _PARSE.format(starting_rule=self.grammar.starting_rule)

        text += self._gen_methods()
        if self.grammar.needed_builtin_functions:
            text += '\n\n'
            text += self._gen_functions()
        if self.options.main:
            text += _MAIN_FOOTER
        else:
            text += _DEFAULT_FOOTER
        return text

    def _state(self) -> str:
        text = ''
        if self.options.memoize:
            text += '        self.cache = {}\n'
        if self.grammar.leftrec_needed or self.grammar.operator_needed:
            text += '        self.seeds = {}\n'
        if self.grammar.leftrec_needed:
            text += '        self.blocked = set()\n'
        if self.grammar.operator_needed:
            text += self._operator_state()
            text += '\n'

        return text

    def _operator_state(self) -> str:
        text = '        self.operators = {}\n'
        for rule, o in self.grammar.operators.items():
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
                text += "            '%s': self.%s,\n" % (op, o.choices[op])
            text += '        }\n'
            text += "        self.operators['%s'] = o\n" % rule
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

    def _load_builtin_functions(self) -> Dict[str, str]:
        blocks = _BUILTIN_FUNCTIONS[:-1].split('\n\n')
        builtins = {}
        for block in blocks:
            name = block[5 : block.find('(')]
            builtins[name] = block + '\n'
        return builtins

    def _gen_methods(self) -> str:
        text = ''
        for rule, method_body in self._methods.items():
            memoize = self.options.memoize and rule.startswith('_r_')
            text += self._gen_method_text(rule, method_body, memoize)
        text += '\n'

        if self.grammar.needed_builtin_rules:
            text += '\n'.join(
                self._builtin_methods[f'r_{name}_']
                for name in sorted(self.grammar.needed_builtin_rules)
            )
            text += '\n'

        text += '\n'.join(
            self._builtin_methods[name]
            for name in sorted(self._needed_methods)
        )
        return text

    def _gen_method_text(self, method_name, method_body, memoize) -> str:
        text = '\n'
        text += '    def %s(self):\n' % method_name
        if memoize:
            text += '        r = self.cache.get(("%s", ' % method_name
            text += 'self.pos))\n'
            text += '        if r is not None:\n'
            text += '            self.val, self.failed, self.pos = r\n'
            text += '            return\n'
            text += '        pos = self.pos\n'
        for line in method_body:
            text += f'        {line}\n'
        if memoize:
            text += f'        self.cache[("{method_name}", pos)] = ('
            text += 'self.val, self.failed, self.pos)\n'
        return text

    def _gen_functions(self) -> str:
        return '\n\n'.join(
            self._builtin_functions[name]
            for name in sorted(self.grammar.needed_builtin_functions)
        )

    def _gen(self, node) -> List[str]:
        # All of the rule methods return a list of lines.
        fn = getattr(self, f'_{node[0]}_')
        return fn(node)

    def _gen_expr(self, node) -> _FormatObj:
        # All of the host methods return a formatter object.
        fn = getattr(self, f'_{node[0]}_')
        return fn(node)

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _action_(self, node) -> List[str]:
        obj = self._gen_expr(node[2][0])
        return flatten(Saw('self._succeed(', obj, ')'))

    def _apply_(self, node) -> List[str]:
        return [f'self.{node[1]}()']

    def _choice_(self, node) -> List[str]:
        lines = ['p = self.pos']
        for subnode in node[2][:-1]:
            lines.extend(self._gen(subnode))
            lines.append('if not self.failed:')
            lines.append('    return')
            lines.append('self._rewind(p)')
        lines.extend(self._gen(node[2][-1]))
        return lines

    def _empty_(self, node) -> List[str]:
        del node
        return ['self._succeed(None)']

    def _label_(self, node) -> List[str]:
        lines = self._gen(node[2][0])
        lines.extend(
            [
                'if not self.failed:',
                f'    v_{node[1].replace("$", "_")} = self.val',
            ]
        )
        return lines

    def _leftrec_(self, node) -> List[str]:
        left_assoc = self.grammar.assoc.get(node[1], 'left') == 'left'
        lines = [
            f'self._leftrec(self.{node[2][0][1]}, '
            + f"'{node[1]}', {str(left_assoc)})"
        ]
        return lines

    def _lit_(self, node) -> List[str]:
        expr = lit.encode(node[1])
        if len(node[1]) == 1:
            method = 'ch'
        else:
            method = 'str'
        return [f'self._{method}({expr})']

    def _not_(self, node) -> List[str]:
        sublines = self._gen(node[2][0])
        lines = (
            [
                'p = self.pos',
                'errpos = self.errpos',
            ]
            + sublines
            + [
                'if self.failed:',
                '    self._succeed(None, p)',
                'else:',
                '    self._rewind(p)',
                '    self.errpos = errpos',
                '    self._fail()',
            ]
        )
        return lines

    def _operator_(self, node) -> List[str]:
        self._needed_methods.add('operator')
        # Operator nodes have no children, but subrules for each arm
        # of the expression cluster have been defined and are referenced
        # from self.grammar.operators[node[1]].choices.
        assert node[2] == []
        return [f"self._operator(f'{node[1]}')"]

    def _paren_(self, node) -> List[str]:
        return self._gen(node[2][0])

    def _post_(self, node) -> List[str]:
        sublines = self._gen(node[2][0])
        if node[1] == '?':
            lines = (
                [
                    'p = self.pos',
                ]
                + sublines
                + [
                    'if self.failed:',
                    '    self._succeed([], p)',
                    'else:',
                    '    self._succeed([self.val])',
                ]
            )
        else:
            lines = ['vs = []']
            if node[1] == '+':
                lines.extend(sublines)
                lines.extend(
                    [
                        'vs.append(self.val)',
                        'if self.failed:',
                        '    return',
                    ]
                )
            lines.extend(
                [
                    'while True:',
                    '    p = self.pos',
                ]
                + ['    ' + line for line in sublines]
                + [
                    '    if self.failed:',
                    '        self._rewind(p)',
                    '        break',
                    '    if self.pos == p:',
                    '        break',
                    '    vs.append(self.val)',
                    'self._succeed(vs)',
                ]
            )
        return lines

    def _pred_(self, node) -> List[str]:
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

    def _range_(self, node) -> List[str]:
        return [
            'self._range(%s, %s)'
            % (lit.encode(node[2][0][1]), lit.encode(node[2][1][1]))
        ]

    def _seq_(self, node) -> List[str]:
        lines = self._gen(node[2][0])
        for subnode in node[2][1:]:
            lines.append('if not self.failed:')
            lines.extend('    ' + line for line in self._gen(subnode))
        return lines

    def _unicat_(self, node) -> List[str]:
        return ['self._unicat(%s)' % lit.encode(node[1])]

    #
    # Handlers for the host nodes in the AST
    #
    def _ll_arr_(self, node) -> _FormatObj:
        if len(node[2]) == 0:
            return '[]'
        args = [self._gen(n) for n in node[2]]
        return Saw('[', Comma(args), ']')

    def _ll_call_(self, node) -> Saw:
        # There are no built-in functions that take no arguments, so make
        # sure we're not being called that way.
        # TODO: Figure out if we need this routine or not when we also
        # fix the quals.
        assert len(node[2]) != 0
        args = [self._gen(n) for n in node[2]]
        return Saw('(', Comma(args), ')')

    def _ll_getitem_(self, node) -> Saw:
        return Saw('[', self._gen(node[2][0]), ']')

    def _ll_lit_(self, node) -> str:
        return lit.encode(node[1])

    def _ll_minus_(self, node) -> Tree:
        return Tree(
            self._gen_expr(node[2][0]), '-', self._gen_expr(node[2][1])
        )

    def _ll_num_(self, node) -> str:
        return node[1]

    def _ll_paren_(self, node) -> _FormatObj:
        return self._gen_expr(node[2][0])

    def _ll_plus_(self, node) -> Tree:
        return Tree(
            self._gen_expr(node[2][0]), '+', self._gen_expr(node[2][1])
        )

    def _ll_qual_(self, node) -> Saw:
        first = node[2][0]
        second = node[2][1]
        if first[0] == 'll_var':
            if second[0] == 'll_call':
                # first is an identifier, but it must refer to a
                # built-in function if second is a call.
                fn = first[1]
                # Note that unknown functions were caught during analysis
                # so we don't have to worry about that here.
                start = f'_{fn}'
            else:
                # If second isn't a call, then first refers to a variable.
                start = self._ll_var_(first)
            saw = self._gen_expr(second)
            if not isinstance(saw, Saw):  # pragma: no cover
                raise TypeError(second)
            saw.start = start + saw.start
            i = 2
        else:
            # TODO: We need to do typechecking, and figure out a better
            # strategy for propagating errors/exceptions.
            saw = self._gen_expr(first)
            if not isinstance(saw, Saw):  # pragma: no cover
                raise TypeError(first)
            i = 1
        next_saw = saw
        for n in node[2][i:]:
            new_saw = self._gen_expr(n)
            if not isinstance(new_saw, Saw):  # pragma: no cover
                raise TypeError(n)
            new_saw.start = next_saw.end + new_saw.start
            next_saw.end = new_saw
            next_saw = new_saw
        return saw

    def _ll_var_(self, node) -> str:
        return 'v_' + node[1].replace('$', '_')

    def _ll_const_(self, node) -> str:
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


_DEFAULT_HEADER = """\
from typing import Any, NamedTuple, Optional
{unicodedata_import}
# pylint: disable=too-many-lines


"""


_DEFAULT_FOOTER = ''


_MAIN_HEADER = """\
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
        self.failed = False
        self.path = path
        self.pos = 0
        self.val = None
"""


_PARSE = """\
    def parse(self):
        self._r_{starting_rule}_()
        if self.failed:
            return Result(None, self._err_str(), self.errpos)
        return Result(self.val, None, self.pos)
"""


_PARSE_WITH_EXCEPTION = """\
    def parse(self):
        try:
            self._r_{starting_rule}_()
            if self.failed:
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


_BUILTIN_METHODS = """\
    def _r_any_(self):
        if self.pos < self.end:
            self._succeed(self.text[self.pos], self.pos + 1)
        else:
            self._fail()

    def _r_end_(self):
        if self.pos == self.end:
            self._succeed(None)
        else:
            self._fail()

    def _ch(self, ch):
        p = self.pos
        if p < self.end and self.text[p] == ch:
            self._succeed(ch, self.pos + 1)
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
        self.failed = True
        self.errpos = max(self.errpos, self.pos)

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

    def _range(self, i, j):
        p = self.pos
        if p != self.end and ord(i) <= ord(self.text[p]) <= ord(j):
            self._succeed(self.text[p], self.pos + 1)
        else:
            self._fail()

    def _rewind(self, newpos):
        self._succeed(None, newpos)

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
        if p < self.end and unicodedata.category(self.text[p]) == cat:
            self._succeed(self.text[p], self.pos + 1)
        else:
            self._fail()
"""

_BUILTIN_FUNCTIONS = """\
def _arrcat(a, b):
    return a + b

def _dict(pairs):
    return dict(pairs)

def _float(s):
    if '.' in s or 'e' in s or 'E' in s:
        return float(s)
    return int(s)

def _hex(s):
    return int(s, base=16)

def _is_unicat(var, cat):
    return unicodedata.category(var) == cat

def _itou(n):
    return chr(n)

def _join(s, vs):
    return s.join(vs)

def _strcat(a, b):
    return a + b

def _utoi(s):
    return ord(s)

def _xtoi(s):
    return int(s, base=16)

def _xtou(s):
    return chr(int(s, base=16))
"""
