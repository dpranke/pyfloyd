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

import textwrap
from typing import Any, Set

from pyfloyd import at_expr
from pyfloyd import datafile
from pyfloyd.analyzer import Grammar
from pyfloyd.ast import Node
from pyfloyd.formatter import flatten, FormatObj, ListObj, VList
from pyfloyd.generator import Generator, GeneratorOptions


class _DFTError(Exception):
    pass


class DatafileGenerator(Generator):
    def __init__(self, host, grammar: Grammar, options: GeneratorOptions):
        super().__init__(host, grammar, options)
        self._local_vars: dict[str, Any] = {}
        self._global_vars: dict[str, Any] = {}

        self._derive_memoize()
        self._derive_local_vars()

        fname = host.join(host.dirname(__file__), 'python.dft')
        df_str = host.read_text_file(fname)
        self._templates = datafile.loads(df_str)
        self._indent = self._templates.get('indent', '    ')

    def _derive_memoize(self):
        def _walk(node):
            if node.t == 'apply':
                if self._options.memoize and node.rule_name.startswith('r_'):
                    name = node.rule_name[2:]
                    node.memoize = (
                        name not in self._grammar.operators
                        and name not in self._grammar.leftrec_rules
                    )
                else:
                    node.memoize = False
            else:
                for c in node.ch:
                    _walk(c)

        _walk(self._grammar.ast)

    def _derive_local_vars(self):
        def _walk(node) -> Set[str]:
            local_vars: Set[str] = set()
            local_vars.update(set(self._local_vars.get(node.t, [])))
            for c in node.ch:
                local_vars.update(_walk(c))
            return local_vars

        for _, node in self._grammar.rules.items():
            node.local_vars = _walk(node)

    def _defmt(self, s: str) -> VList:
        vl = VList(textwrap.dedent(s).splitlines())
        return vl

    def _defmtf(self, s: str, **kwargs) -> VList:
        vl = VList(textwrap.dedent(s).format(**kwargs).splitlines())
        return vl

    def _fmt(self, obj: FormatObj) -> str:
        text = '\n'.join(flatten(obj, indent=self._indent)) + '\n'
        return text

    def generate(self) -> str:
        self._global_vars['grammar'] = self._grammar
        self._global_vars['generator_options'] = self._options
        return self._eval_template('generate')

    # TODO: Move these methods from Generator to a different class.
    def _gen_extern(self, name: str) -> str:
        raise NotImplementedError

    def _gen_invoke(self, fn: str, *args) -> FormatObj:
        raise NotImplementedError

    def _gen_thisvar(self, name: str) -> str:
        raise NotImplementedError

    def _gen_rulename(self, name: str) -> str:
        raise NotImplementedError

    def _ty_regexp(self, node: Node) -> ListObj:
        raise NotImplementedError

    def _eval_template(self, template, args=None) -> str:
        del args
        v = self._templates[template]
        if isinstance(v, str):
            return self._eval_text(v)
        raise NotImplementedError

    def _eval_text(self, text) -> str:
        v, err, pos = at_expr.parse(text, '-')
        if err:
            raise _DFTError('unexpected at-expr parse error: ' + err)
        if pos != len(text):
            raise _DFTError('at-expr parse did not consume everything')
        assert isinstance(v, list)

        r = self._eval_exprs(v, '\n' in text)
        return r

    def _eval_exprs(self, exprs, multiline: bool):
        del multiline

        def _is_blank(s):
            i = len(s) - 1
            indent = 0
            while i >= 0:
                if s[i] == ' ':
                    i -= 1
                    indent += 1
                    continue
                if s[i] == '\n':
                    return True, indent
                return False, 0
            return False, 0

        s = ''
        skip_newline = False
        for i, expr in enumerate(exprs):
            if isinstance(expr, str):
                if expr.startswith('\n') and skip_newline:
                    skip_newline = False
                    s += expr[1:]
                    continue
                s += expr
                continue
            if (
                isinstance(expr, list)
                and isinstance(expr[0], list)
                and len(expr[0]) > 0
                and expr[0][0] == 'symbol'
            ):
                res = self._eval_fn(expr[0][1], expr[1:])
            elif isinstance(expr, list) and expr[0] == 'symbol':
                res = self._eval_fn(expr[1])
            else:
                assert False, f'Unknown expr {expr}'

            is_blank, indent = _is_blank(s)
            if i < len(exprs) and exprs[i + 1].startswith('\n') and is_blank:
                # If the expr is on a line of its own, if it evalues to
                # '', trim the whole line. Otherwise, splice the result
                # into the string, indenting each line as appropriate.
                if res == '':
                    skip_newline = True
                    s = s[:-indent]
                    continue
                lines = res.splitlines()
                s += lines[0]
                for line in lines[1:]:
                    s += '\n' + ' ' * indent + line
            else:
                s += res

        return s

    def _eval_expr(self, expr):
        if isinstance(expr, str):
            return expr
        assert isinstance(expr, list) and expr[0] == 'symbol'
        return self._eval_template(expr[1])

    def _eval_fn(self, symbol, args=None):
        args = args or []
        if symbol == 'if':
            return self._eval_if(args)
        found, v = self._lookup_global(symbol)
        if found:
            return v
        if symbol in self._templates:
            return self._eval_template(symbol, args)
        raise _DFTError(f'Unknown symbol "{symbol}"')

    def _eval_if(self, args):
        assert len(args) == 3, (
            f'Wrong number of args passed to `if`: repr{args}'
        )
        assert isinstance(args[0], list)
        assert len(args[0]) == 2
        assert args[0][0] == 'symbol'
        v = self._lookup(args[0][1])
        if v:
            return self._eval_expr(args[1])
        return self._eval_expr(args[2])

    def _lookup(self, symbol):
        if symbol == 'true':
            return True
        if symbol == 'false':
            return False
        symbols = symbol.split('.')
        if symbols[0] in self._global_vars:
            v = self._global_vars[symbols[0]]
        else:
            v = self._templates[symbols[0]]
        for attr in symbols[1:]:
            v = getattr(v, attr)
        return v

    def _lookup_global(self, symbol):
        symbols = symbol.split('.')
        if symbols[0] not in self._global_vars:
            return False, None
        v = self._global_vars[symbols[0]]
        for attr in symbols[1:]:
            v = getattr(v, attr)
        return True, v
