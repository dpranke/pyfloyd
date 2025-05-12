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

from typing import Any, Optional, Set

from pyfloyd import ast
from pyfloyd import at_expr
from pyfloyd import datafile
from pyfloyd.analyzer import Grammar
from pyfloyd.formatter import (
    flatten,
    Comma,
    FormatObj,
    HList,
    Indent,
    Saw,
    VList,
)
from pyfloyd.generator import Generator, GeneratorOptions
from pyfloyd import lisp


class DatafileGenerator(Generator):
    def __init__(self, host, grammar: Grammar, options: GeneratorOptions):
        super().__init__(host, grammar, options)
        self._local_vars: dict[str, Any] = {}

        self._derive_memoize()
        self._derive_local_vars()

        self._interpreter = lisp.Interpreter(
            values={
                'grammar': grammar,
                'generator_options': options,
                'at_expr': self.f_at_expr,
                'comma': self.f_comma,
                'hlist': self.f_hlist,
                'indent': self.f_indent,
                'invoke': self.f_invoke,
                'saw': self.f_saw,
                'template': self.f_template,
                'vlist': self.f_vlist,
            },
            fexprs={
                'at': self.fexpr_at,
            },
            is_foreign=self.is_foreign,
            eval_foreign=self.eval_foreign,
        )

        self._host = host
        if 'file' in options.defines:
            fname = options.defines.get('file')
        else:
            fname = self._host.join(host.dirname(__file__), 'python.dft')
        self._process_template_file(fname)

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

    def _process_template_file(self, fname):
        df_str = self._host.read_text_file(fname)

        def _parse_bareword(s: str, as_key: bool) -> Any:
            if as_key:
                return s
            return ['symbol', s]

        templates = datafile.loads(df_str, parse_bareword=_parse_bareword)
        for t, v in templates.items():
            if isinstance(v, str):
                # TODO: Fix dedenting properly.
                if v.startswith('\n'):
                    v = v[1:]
                expr = [['symbol', 'fn'], [], [['symbol', 'at_expr'], v]]
                self._interpreter.define(t, expr)
            else:
                lisp.check(lisp.is_list(v))
                if v[0] == ['symbol', 'fn'] or v[0] == ['symbol', 'at']:
                    self._interpreter.define(t, v)
                else:
                    expr = [['symbol', 'fn'], [], v]
                    self._interpreter.define(t, expr)
        if 'indent' in templates:
            self._indent = templates['indent']

    def is_foreign(self, expr: Any, env: lisp.Env) -> bool:
        del env
        return isinstance(expr, ast.Node)

    def eval_foreign(self, expr: Any, env: lisp.Env) -> Any:
        assert self.is_foreign(expr, env)
        return expr

    def generate(self) -> str:
        s = self._interpreter.eval([['symbol', 'generate']])
        lines = s.splitlines()
        res = ['' if line.isspace() else line for line in lines]
        return '\n'.join(res) + '\n'

    def f_template(self, name: str) -> str:
        tmpl = self._interpreter.env.get(name)
        lisp.check(lisp.is_fn(tmpl))
        return tmpl()

    # pylint: disable=too-many-statements
    def f_at_expr(self, args, env) -> Any:
        del env
        if len(args) > 1:
            env = lisp.Env(parent=self._interpreter.env)
            names = args[0]
            for i, name in enumerate(names):
                env.set(name, args[i + 1])
        else:
            env = None
        text = args[-1]
        lisp.check(lisp.is_str(text))
        exprs, err, pos = at_expr.parse(text, '-')
        if err:
            raise lisp.Error('unexpected at-expr parse error: ' + err)
        if pos != len(text):
            raise lisp.Error('at-expr parse did not consume everything')
        assert isinstance(exprs, list)

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

            res = self._interpreter.eval(expr, env)
            while (
                lisp.is_list(res)
                and len(res) > 0
                and res[0] == ['symbol', 'at_expr']
            ):
                res = self._interpreter.eval(res, env)

            # If `@foo` resolves to a lambda with no parameters,
            # evaluate that.
            if lisp.is_fn(res) and len(res.params) == 0:
                r = res
                res = r([], env)

            is_blank, indent = _is_blank(s)
            if (
                i < len(exprs) - 1
                and exprs[i + 1].startswith('\n')
                and is_blank
            ):
                # If the expr is on a line of its own, if it evalues to
                # '', trim the whole line. Otherwise, splice the result
                # into the string, indenting each line as appropriate.
                if res == '':
                    skip_newline = True
                    if indent:
                        s = s[:-indent]
                    continue
                lines = res.splitlines()
                s += lines[0]
                for line in lines[1:]:
                    s += '\n' + ' ' * indent + line
                if res.endswith('\n'):
                    s += '\n'
            else:
                if isinstance(res, FormatObj):
                    lines = flatten(res, 80)
                    s += lines[0]
                    for line in lines[1:]:
                        s += '\n' + ' ' * indent + line
                    continue
                if isinstance(res, list):
                    res = self._interpreter.eval(res, env)
                s += res
            if (
                res.endswith('\n')
                and i < len(exprs)
                and exprs[i + 1].startswith('\n')
            ):
                skip_newline = True

        return s

    # pylint: enable=too-many-statements

    def fexpr_at(self, args: list[Any], env: lisp.Env) -> Any:
        params, text = args
        names = [p[1] for p in params]
        return lisp.Fn(
            self._interpreter,
            params,
            [['symbol', 'at_expr']]
            + [[['symbol', 'list']] + names]
            + params
            + [text],
            env,
        )

    def f_comma(self, args, env) -> Any:
        del env
        return Comma(args)

    def f_hlist(self, args, env) -> Any:
        del env
        return HList(args)

    def f_indent(self, args, env) -> Any:
        del env
        return Indent(args[0])

    def f_vlist(self, args, env) -> Any:
        del env
        return VList(args)

    def f_saw(self, args, env) -> Any:
        del env
        start, mid, end = args
        return Saw(start, mid, end)

    def f_invoke(self, args, env) -> Any:
        exprs = [['symbol', args[0]]] + args[1:]
        return self._interpreter.eval(exprs, env)
