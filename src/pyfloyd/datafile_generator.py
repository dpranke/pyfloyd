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

from typing import Any

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
        interp.add_foreign_handler(self._eval_node)
        interp.env.set('grammar', grammar)
        interp.env.set('generator_options', self.options)
        interp.define_native_fn('at_exp', self.f_at_exp, types=['str'])
        interp.define_native_fn('comma', self.f_comma)
        interp.define_native_fn('hl', self.f_hl)
        interp.define_native_fn('hl_l', self.f_hl_l, types=['list'])
        interp.define_native_fn('ind', self.f_ind)
        interp.define_native_fn('ind_l', self.f_ind_l, types=['list'])
        interp.define_native_fn('invoke', self.f_invoke)
        interp.define_native_fn('lit', self.f_lit)
        interp.define_native_fn('saw', self.f_saw)
        interp.define_native_fn('tree', self.f_tree)
        interp.define_native_fn('tri', self.f_tri)
        interp.define_native_fn('vl', self.f_vl)
        interp.define_native_fn('vl_l', self.f_vl_l)

        self._host = host
        if 'file' in options.generator_options:
            fname = options.generator_options.get('file')
        else:
            fname = self._host.join(host.dirname(__file__), 'python.dft')
        self._process_template_file(fname)

        # TODO: Figure out how to correctly handle non-multi-char literals.
        if grammar.ch_needed and not grammar.str_needed:
            grammar.str_needed = True
            grammar.needed_operators = sorted(
                grammar.needed_operators + ['str']
            )
        if self.options.memoize:
            grammar.needed_operators = sorted(
                grammar.needed_operators + ['memoize']
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

    def _process_template_file(self, fname):
        df_str = self._host.read_text_file(fname)
        templates = datafile.loads(
            df_str,
            parse_bareword=self._parse_bareword,
            custom_tags={'@': self._to_at_exp},
        )
        for t, v in templates.items():
            self._interpreter.define(t, v)

    def _parse_bareword(self, s: str, as_key: bool) -> Any:
        if as_key:
            return s
        return ['symbol', s]

    def _to_at_exp(self, ty, tag, obj, as_key=False):
        assert ty == 'string' and tag == '@' and not as_key, (
            f'Uexpected tag fn invocation: '
            f'ty={ty} tag={tag} obj={repr(obj)}, as_key={as_key}'
        )
        s = datafile.dedent(obj)
        return [['symbol', 'fn'], [], [['symbol', 'at_exp'], s]]

    def _eval_node(
        self, expr: Any, env: lisp_interpreter.Env
    ) -> tuple[bool, Any]:
        del env
        if isinstance(expr, m_grammar.Node):
            return True, expr
        return False, None

    def generate(self) -> str:
        obj = self._interpreter.eval([['symbol', 'generate']])
        if self.options.generator_options.get('as_ll'):
            fmt_fn = formatter.flatten_as_lisplist
        else:
            fmt_fn = formatter.flatten
        lines = fmt_fn(obj, self.options.line_length, self.options.indent)
        return '\n'.join(lines) + '\n'

    def f_at_exp(self, args, env) -> Any:
        exprs, err, _ = at_exp_parser.parse(args[0], '-')
        lisp_interpreter.check(
            err is None, f'Unexpected at_exp parse error: {err}'
        )
        values = [self._interpreter.eval(expr, env) for expr in exprs]
        return _process_at_exp_values(values)

    def f_comma(self, args, env) -> Any:
        del env
        return formatter.Comma(*args[0])

    def f_hl(self, args, env) -> Any:
        """Returns an HList of the args passed to the function."""
        del env
        return formatter.HList(*args)

    def f_hl_l(self, args, env) -> Any:
        """Returns an Hlist of the list in the first arg."""
        del env
        return formatter.HList(*args[0])

    def f_ind(self, args, env) -> Any:
        """Returns an indented VList of the args passed to the function."""
        del env
        vl = formatter.VList()
        vl += args
        return formatter.Indent(vl)

    def f_ind_l(self, args, env) -> Any:
        """Returns an indented VList of the list in the first arg."""
        del env
        vl = formatter.VList()
        vl += args[0]
        return formatter.Indent(vl)

    def f_invoke(self, args, env) -> Any:
        """Invoke the template named in arg 1, passing it the remaining args."""
        first = self._interpreter.eval(args[0], env)
        obj = env.get(first)
        if lisp_interpreter.is_str(obj):
            return obj
        return self._interpreter.eval([['symbol', first]] + args[1:], env)

    def f_lit(self, args, env) -> Any:
        del env
        return string_literal.encode(args[0])

    def f_saw(self, args, env) -> Any:
        del env
        return formatter.Saw(*args[0])

    def f_tree(self, args, env) -> Any:
        del env
        return formatter.Tree(*args)

    def f_tri(self, args, env) -> Any:
        del env
        return formatter.Triangle(*args)

    def f_vl(self, args, env) -> Any:
        del env
        vl = formatter.VList()
        vl += args
        return vl

    def f_vl_l(self, args, env) -> Any:
        del env
        vl = formatter.VList()
        vl += args[0]
        return vl


def _process_at_exp_values(values):
    results = []

    # If the only thing on the line was a newline, keep it.
    if values == ['\n']:
        return formatter.VList('')

    # Iterate through the list of objects returned from evaluating the
    # at-exp string. Whenever we hit a newline, look at the values since
    # the last newline and decide what to do with them.
    current_values = []
    for v in values:
        if v == '\n':
            results.extend(_process_one_line_of_values(current_values))
            current_values = []
        else:
            current_values.append(v)

    # Also process any arguments following the last newline (or, all
    # of the arguments, if there was no newline).
    if len(current_values) != 0:
        results.extend(_process_one_line_of_values(current_values))
    vl = formatter.VList()
    for result in results:
        vl += result
    return vl


def _process_one_line_of_values(values):
    # Drop the line if appropriate (see below). This allows embedded
    # at-exps and functions to avoid trailing newlines and unwanted
    # blank lines resulting in the output.
    if _should_drop_the_line(values):
        return []

    # If there is just one value on the line and it is a FormatObj, return it.
    if len(values) == 1 and isinstance(values[0], formatter.FormatObj):
        return [values[0]]

    # If the set is a series of spaces followed by a FormatObj,
    # indent and return the format obj.
    if (
        len(values) == 2
        and isinstance(values[0], str)
        and values[0].isspace()
        and isinstance(values[1], formatter.FormatObj)
    ):
        return [formatter.Indent(values[1])]

    # If everything is a string or an HList, return an HList containing them.
    if all(isinstance(v, (str, formatter.HList)) for v in values):
        return [formatter.HList(*values)]

    assert False, f'unexpected line of values: {repr(values)}'


# A line of values should be dropped (or skipped) when:
# - At least one value is either None or a VList with no elements.
# - Any other values are whitespace.
def _should_drop_the_line(values):
    has_empty_value = False
    has_non_empty_string = False
    for v in values:
        if v is None:
            has_empty_value = True
        if isinstance(v, formatter.VList) and v.is_empty():
            has_empty_value = True
        if isinstance(v, str) and not v.isspace():
            has_non_empty_string = True
    return has_empty_value and not has_non_empty_string
