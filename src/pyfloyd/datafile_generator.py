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

from typing import Any, Set

from pyfloyd import ast
from pyfloyd import at_exp_parser
from pyfloyd import datafile
from pyfloyd.analyzer import Grammar
from pyfloyd.formatter import (
    flatten,
    Comma,
    FormatObj,
    HList,
    Indent,
    Lit,
    Saw,
    VList,
)
from pyfloyd.generator import Generator
from pyfloyd import lisp_interpreter


class DatafileGenerator(Generator):
    def __init__(self, host, grammar: Grammar, options):
        super().__init__(host, grammar, options)
        self._local_vars: dict[str, Any] = {}

        self._derive_memoize()
        self._derive_local_vars()

        self._interpreter = interp = lisp_interpreter.Interpreter()
        interp.env.set('grammar', grammar)
        interp.env.set('options', self.options)
        interp.define_native_fn('at_exp', self.f_at_exp)
        interp.define_native_fn('comma', self.f_comma)
        interp.define_native_fn('hl', self.f_hl)
        interp.define_native_fn('hl_l', self.f_hl_l, types=['list'])
        interp.define_native_fn('ind', self.f_ind)
        interp.define_native_fn('ind_l', self.f_ind_l, types=['list'])
        interp.define_native_fn('invoke', self.f_invoke)
        interp.define_native_fn('lit', self.f_lit)
        interp.define_native_fn('saw', self.f_saw)
        interp.define_native_fn('vl', self.f_vl)
        interp.define_native_fn('vl_l', self.f_vl_l)
        interp.is_foreign = self.is_foreign
        interp.eval_foreign = self.eval_foreign

        self._host = host
        if 'file' in options.defines:
            fname = options.defines.get('file')
        else:
            fname = self._host.join(host.dirname(__file__), 'python.dft')
        self._process_template_file(fname)

    def _derive_memoize(self):
        def _walk(node):
            if node.t == 'apply':
                if self.options.memoize and node.rule_name.startswith('r_'):
                    name = node.rule_name[2:]
                    node.memoize = (
                        name not in self.grammar.operators
                        and name not in self.grammar.leftrec_rules
                    )
                else:
                    node.memoize = False
            else:
                for c in node.ch:
                    _walk(c)

        _walk(self.grammar.ast)

    def _derive_local_vars(self):
        def _walk(node) -> Set[str]:
            local_vars: Set[str] = set()
            local_vars.update(set(self._local_vars.get(node.t, [])))
            for c in node.ch:
                local_vars.update(_walk(c))
            return local_vars

        for _, node in self.grammar.rules.items():
            node.local_vars = _walk(node)

    def _parse_bareword(self, s: str, as_key: bool) -> Any:
        if as_key:
            return s
        return ['symbol', s]

    def _process_template_file(self, fname):
        df_str = self._host.read_text_file(fname)
        templates = datafile.loads(df_str, parse_bareword=self._parse_bareword)
        interp = self._interpreter
        for t, v in templates.items():
            if isinstance(v, str):
                # TODO: Fix dedenting properly.
                if v.startswith('\n'):
                    v = v[1:]
                if v.startswith('@['):
                    stop = v.index('{')
                    exprs, err, _ = at_exp_parser.parse(v[0:stop])
                    lisp_interpreter.check(
                        err is None, f'Failed to parse at-exp `{v}`'
                    )
                    lisp_interpreter.check(len(exprs) == 1)
                    expr = exprs[0]
                    lisp_interpreter.check(
                        exprs[0][0] == ['symbol', 'list'],
                        f'Unexpected at-exp parse result `{exprs}`',
                    )
                    names = [expr[1] for expr in exprs[0][1:]]
                    body_text = v[stop + 1 : -1]
                else:
                    names = []
                    body_text = v
                if '@' not in body_text:
                    self._interpreter.env.set(t, v)
                else:
                    body = [['symbol', 'at_exp'], body_text]
                    fn = lisp_interpreter.UserFn(interp, names, body)
                    self._interpreter.env.set(t, fn)
            else:
                lisp_interpreter.check(
                    lisp_interpreter.is_list(v), f"{v} isn't a list"
                )
                if v[0] == ['symbol', 'fn']:
                    self._interpreter.define(t, v)
                else:
                    expr = [['symbol', 'fn'], [], v]
                    self._interpreter.define(t, expr)

    # TODO: this should really be a check for whether you can handle
    # this data type, not whether it is foreign.
    def is_foreign(self, expr: Any, env: lisp_interpreter.Env) -> bool:
        if isinstance(expr, ast.Node):
            return True
        return lisp_interpreter.is_foreign(expr, env)

    def eval_foreign(self, expr: Any, env: lisp_interpreter.Env) -> Any:
        assert self.is_foreign(expr, env)
        return expr

    def generate(self) -> str:
        s = self._interpreter.eval([['symbol', 'generate']])
        lines = s.splitlines()
        res = ['' if line.isspace() else line for line in lines]
        return '\n'.join(res) + '\n'

    def f_at_exp(self, args, env) -> Any:
        if len(args) > 1:
            new_env = lisp_interpreter.Env(parent=self._interpreter.env)
            names = args[0]
            for i, name in enumerate(names):
                new_env.set(name, args[i + 1])
        else:
            new_env = env
        text = args[-1]
        lisp_interpreter.check(lisp_interpreter.is_str(text))
        exprs, err, _ = at_exp_parser.parse(text, '-')
        lisp_interpreter.check(
            err is None, f'Unexpected at-exp parse error: {err}'
        )
        assert isinstance(exprs, list)

        s = ''
        for i, expr in enumerate(exprs):
            obj = self._interpreter.eval(expr, new_env)

            # If `@foo` resolves to a lambda with no parameters,
            # evaluate that.
            if lisp_interpreter.is_fn(obj) and len(obj.params) == 0:
                obj = obj.call([], env)

            if isinstance(obj, FormatObj):
                obj = '\n'.join(flatten(obj, 80))

            if isinstance(obj, list):
                # TODO: Is this the best thing to do here?
                obj = ''.join(obj)

            lisp_interpreter.check(
                lisp_interpreter.is_str(obj),
                f'Unexpected at-exp result `{repr(obj)}`',
            )

            nl_is_next = newline_is_next(exprs, i)

            is_blank, num_spaces = ends_blank(s)
            num_to_chomp, res = self._format(
                obj, is_blank, num_spaces, nl_is_next
            )

            if num_to_chomp:
                s = s[:-num_to_chomp]
            s += res
        return s

    def _format(self, s, is_blank, num_spaces, nl_is_next) -> tuple[int, str]:
        if nl_is_next:
            if is_blank and s == '':
                # If the expr is on a line of its own, and it evalues to
                # '', trim the whole line. Otherwise, splice the result
                # into the string, indenting each line as appropriate.
                return num_spaces + 1, ''

            s = indent(s, num_spaces, nl_is_next)

        return 0, s

    def f_comma(self, args, env) -> Any:
        del env
        return Comma(args[0])

    def f_hl(self, args, env) -> Any:
        """Returns an HList of the args passed to the function."""
        del env
        return HList(args)

    def f_hl_l(self, args, env) -> Any:
        """Returns an Hlist of the list in the first arg."""
        del env
        return HList(args[0])

    def f_ind(self, args, env) -> Any:
        """Returns an indented VList of the args passed to the function."""
        del env
        return Indent(VList(args))

    def f_ind_l(self, args, env) -> Any:
        """Returns an indented VList of the list in the first arg."""
        del env
        return Indent(VList(args[0]))

    def f_invoke(self, args, env) -> Any:
        """Invoke the template named in arg 1, passing it the remaining args."""
        first = self._interpreter.eval(args[0], env)
        obj = env.get(first)
        if lisp_interpreter.is_str(obj):
            return obj
        return self._interpreter.eval([['symbol', first]] + args[1:], env)

    def f_lit(self, args, env) -> Any:
        del env
        return Lit(args[0])

    def f_saw(self, args, env) -> Any:
        del env
        start, mid, end = args
        return Saw(start, mid, end)

    def f_vl(self, args, env) -> Any:
        del env
        return VList(args)

    def f_vl_l(self, args, env) -> Any:
        del env
        return VList(args[0])


def ends_blank(s):
    """Returns whether the string ends in a newline followed by a number
    of spaces and how many spaces that is."""
    i = len(s) - 1
    num_spaces = 0
    while i >= 0 and s[i] == ' ':
        i -= 1
        num_spaces += 1
    return (i >= 0 and s[i] == '\n'), num_spaces


def newline_is_next(exprs, i):
    if i < len(exprs) - 1:
        return lisp_interpreter.is_str(exprs[i + 1]) and exprs[
            i + 1
        ].startswith('\n')
    return False


def indent(s, num_spaces, nl_is_next):
    """Returns a string with all but the first line indented `num_spaces`."""
    if not s:
        return ''

    res = ''
    lines = s.splitlines()
    res += lines[0]
    for line in lines[1:]:
        res += '\n' + ' ' * num_spaces + line
    if s.endswith('\n') and not nl_is_next:
        res += '\n'
    return res
