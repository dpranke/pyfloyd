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

from typing import Any, Optional

from pyfloyd import (
    at_exp_parser,
    datafile,
    formatter,
    generator,
    grammar as m_grammar,
    lisp_interpreter,
    string_literal,
    support,
)


class DatafileGenerator(generator.Generator):
    name = 'datafile'
    help_str = 'Generator code from a datafile template'
    indent = '    '

    def __init__(
        self,
        host: support.Host,
        grammar: m_grammar.Grammar,
        options: generator.GeneratorOptions,
    ):
        super().__init__(host, grammar, options)
        options.generator_options = options.generator_options or {}
        self._fl = options.formatter_list
        self._local_vars: dict[str, Any] = {}

        self._derive_memoize()
        self._derive_local_vars()

        self._interpreter = interp = lisp_interpreter.Interpreter()
        interp.env.set('grammar', grammar)
        interp.env.set('generator_options', self.options)
        interp.define_native_fn('at_exp', self.f_at_exp)
        interp.define_native_fn('comma', self.f_comma)
        interp.define_native_fn('hl', self.f_hl)
        interp.define_native_fn('hl_l', self.f_hl_l, types=['list'])
        interp.define_native_fn('ind', self.f_ind)
        interp.define_native_fn('ind_l', self.f_ind_l, types=['list'])
        interp.define_native_fn('invoke', self.f_invoke)
        interp.define_native_fn('lit', self.f_lit)
        interp.define_native_fn('saw', self.f_saw)
        interp.define_native_fn('tree', self.f_tree)
        interp.define_native_fn('vl', self.f_vl)
        interp.define_native_fn('vl_l', self.f_vl_l)
        interp.is_foreign = self.is_foreign
        interp.eval_foreign = self.eval_foreign

        self._host = host
        if 'file' in options.generator_options:
            fname = options.generator_options.get('file')
        else:
            fname = self._host.join(host.dirname(__file__), 'python.dft')
        self._process_template_file(fname)

        # TODO: figure out how to handle non-multi-char literals.
        if grammar.ch_needed and not grammar.str_needed:
            grammar.str_needed = True
            grammar.needed_operators = sorted(
                grammar.needed_operators + ['str']
            )

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
        def _walk(node) -> set[str]:
            local_vars: set[str] = set()
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
        templates = datafile.loads(
            df_str,
            parse_bareword=self._parse_bareword,
            custom_tags={'@': self._to_at_exp},
        )
        for t, v in templates.items():
            self._interpreter.define(t, v)

    def _to_at_exp(self, ty, tag, obj, as_key=False):
        assert ty == 'string' and tag == '@' and not as_key, (
                f'Uexpected tag fn invocation: '
                f'ty={ty} tag={tag} obj={repr(obj)}, as_key={as_key}'
            )
        s = datafile.dedent(obj)
        return [['symbol', 'fn'], [], [['symbol', 'at_exp'], s]]

    # TODO: this should really be a check for whether you can handle
    # this data type, not whether it is foreign.
    def is_foreign(self, expr: Any, env: lisp_interpreter.Env) -> bool:
        if isinstance(expr, m_grammar.Node):
            return True
        return lisp_interpreter.is_foreign(expr, env)

    def eval_foreign(self, expr: Any, env: lisp_interpreter.Env) -> Any:
        assert self.is_foreign(expr, env)
        return expr

    def generate(self) -> str:
        obj = self._interpreter.eval([['symbol', 'generate']])

        if self.options.generator_options.get('as_ll'):
            fmt_fn = formatter.flatten_as_lisplist
        else:
            fmt_fn = formatter.flatten

        lines = fmt_fn(obj, self.options.line_length, self.options.indent)
        return (
            # '\n'.join('' if line.isspace() else line for line in lines)
            '\n'.join(lines) + '\n'
        )

    def f_at_exp(self, args, env) -> Any:
        # pylint: disable=too-many-statements
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

        objs: list[Optional[formatter.El]] = []
        for i, expr in enumerate(exprs):
            obj = self._interpreter.eval(expr, new_env)
            objs.append(obj)
        return _chunk_objs(objs)
        # return formatter.VList(objs)

    def f_comma(self, args, env) -> Any:
        del env
        return formatter.Comma(args[0])

    def f_hl(self, args, env) -> Any:
        """Returns an HList of the args passed to the function."""
        del env
        return formatter.HList(args)

    def f_hl_l(self, args, env) -> Any:
        """Returns an Hlist of the list in the first arg."""
        del env
        return formatter.HList(args[0])

    def f_ind(self, args, env) -> Any:
        """Returns an indented VList of the args passed to the function."""
        del env
        return formatter.Indent(formatter.VList(args))

    def f_ind_l(self, args, env) -> Any:
        """Returns an indented VList of the list in the first arg."""
        del env
        return formatter.Indent(formatter.VList(args[0]))

    def f_invoke(self, args, env) -> Any:
        """Invoke the template named in arg 1, passing it the remaining args."""
        first = self._interpreter.eval(args[0], env)
        obj = env.get(first)
        if lisp_interpreter.is_str(obj):
            return obj
        return self._interpreter.eval([['symbol', first]] + args[1:], env)

    def f_lit(self, args, env) -> Any:
        del env
        return formatter.Lit(string_literal.encode(args[0]))

    def f_saw(self, args, env) -> Any:
        del env
        start, mid, end = args
        return formatter.Saw(start, mid, end)

    def f_tree(self, args, env) -> Any:
        del env
        left, op, right = args
        return formatter.Tree(left, op, right)

    def f_vl(self, args, env) -> Any:
        del env
        return formatter.VList(args)

    def f_vl_l(self, args, env) -> Any:
        del env
        return formatter.VList(args[0])


def _chunk_objs(objs):
    results = []
    n_objs = len(objs)
    i = 0
    tmp = []
    use_hl = True
    while i < n_objs:
        obj = objs[i]
        tmp.append(obj)
        if obj == '\n':
            results.extend(_chunk(tmp))
            tmp = []
        i += 1
    results.extend(_chunk(tmp))
    if len(results) == 0:
        return ''
    if len(results) == 1:
        return results[0]
    return formatter.VList(results)


def _chunk(tmp):
    results = []
    if tmp == ['\n']:
        return ['']
    if all(_empty(t) for t in tmp):
        return []
    if (len(tmp) == 1 and isinstance(tmp[0], formatter.FormatObj)) or (
        len(tmp) == 2
        and isinstance(tmp[0], formatter.FormatObj)
        and tmp[1] == '\n'
    ):
        return [tmp[0]]
    elif (
        len(tmp) == 3
        and isinstance(tmp[0], str)
        and tmp[0].isspace()
        and isinstance(tmp[1], formatter.FormatObj)
    ):
        return [formatter.Indent([tmp[1]])]
    elif all(isinstance(t, (str, formatter.HList)) for t in tmp):
        if len(tmp) == 2 and tmp[-1] == '\n':
            return [tmp[0]]
        elif tmp[-1] == '\n':
            return [formatter.HList(tmp[:-1])]
        else:
            return [formatter.HList(tmp)]
    else:
        assert False, f'unexpected chunk case: {repr(tmp)}'
        results.append(tmp)


def _empty(t):
    if t is None:
        return True
    if isinstance(t, formatter.VList):
        return t.is_empty()
    if isinstance(t, str):
        return t.isspace()
    return False


def _format(s, is_blank, num_spaces, nl_is_next) -> tuple[int, str]:
    if nl_is_next:
        if is_blank and s == '':
            # If the expr is on a line of its own, and it evalues to
            # '', trim the whole line. Otherwise, splice the result
            # into the string, indenting each line as appropriate.
            return num_spaces + 1, ''

        s = indent(s, num_spaces, nl_is_next)

    return 0, s


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
    del nl_is_next
    lines = formatter.splitlines(s)
    res = ''
    for line in lines[1:]:
        if line == '\n':
            res += line
        else:
            res += ' ' * num_spaces + line
    return res
