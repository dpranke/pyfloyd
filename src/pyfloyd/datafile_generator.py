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
    at_exp,
    datafile,
    formatter,
    generator,
    grammar as m_grammar,
    lisp_interpreter,
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
        self.datafile: dict[str, Any] = {
            'name': None,
            'starting_template': None,
            'indent': 2,
            'ext': None,
            'local_vars': {},
            'templates': {},
        }
        self.df_keys_to_merge = {'local_vars', 'templates'}
        options.generator_options = options.generator_options or {}

        self._interpreter = interp = lisp_interpreter.Interpreter()
        interp.add_foreign_handler(self._eval_node)
        interp.env.set('grammar', grammar)
        interp.env.set('generator_options', self.options)
        interp.define_native_fn('invoke', self.f_invoke)

        default_template = options.get('template', 'python')
        path = self._find_datafile(default_template)
        self._load_datafiles(path)
        self.name = self.datafile['name']
        self.ext = self.datafile['ext']
        self.options.indent = self.datafile['indent']
        if isinstance(self.options.indent, int):
            self.options.indent = ' ' * self.options.indent
        self.options.line_length = self.datafile.get('line_length', 79)

        at_exp.bind_at_exps(interp, self.options.indent)

        self._process_templates()
        self._derive_local_vars()

    def _derive_local_vars(self):
        df_locals = self.datafile.get('local_vars', {})
        if not df_locals:
            return

        def _walk(node) -> set[str]:
            local_vars: set[str] = set()
            local_vars.update(set(sym[1] for sym in df_locals.get(node.t, [])))
            for c in node.ch:
                local_vars.update(_walk(c))
            return local_vars

        for _, node in self.grammar.rules.items():
            node.local_vars = _walk(node)

    def _find_datafile(self, name):
        if self.host.exists(name):
            return name
        _, ext = self.host.splitext(name)
        if ext == '':
            name += '.dft'
        path = self.host.join(self.host.dirname(__file__), name)
        if not self.host.exists(path):
            raise ValueError(f"template file '{name}' not found")
        return path

    def _load_datafiles(self, name):
        path = self._find_datafile(name)
        filename = self.host.relpath(path)
        df_str = self.host.read_text_file(path)
        df = datafile.loads(
            df_str,
            parse_bareword=self._parse_bareword,
            custom_tags={'@': self._to_at_exp, 'q': self._to_quoted_list},
            filename=filename,
        )
        if 'inherit' in df:
            for base in df['inherit']:
                self._load_datafiles(base)
        self._merge_datafile(df)

    def _merge_datafile(self, df):
        # pylint: disable=consider-using-dict-items
        for df_key in self.datafile:
            if df_key in df:
                if df_key in self.df_keys_to_merge:
                    for k, v in df[df_key].items():
                        if (
                            df_key == 'templates'
                            and isinstance(v, str)
                            and '\n' in v
                        ):
                            obj = formatter.split_to_objs(
                                v, self.options.indent
                            )
                        else:
                            obj = v
                        self.datafile[df_key][k] = obj
                else:
                    self.datafile[df_key] = df[df_key]

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

    def _to_quoted_list(self, ty, tag, obj, as_key=False):
        assert ty == 'array' and tag == 'q' and not as_key, (
            f'Uexpected tag fn invocation: '
            f'ty={ty} tag={tag} obj={repr(obj)}, as_key={as_key}'
        )
        return [['symbol', 'quote'], obj]

    def _process_templates(self):
        data = self.datafile
        funcs = {}
        for t, v in data['templates'].items():
            if isinstance(v, list) and len(v) > 0 and v[0] == '@fn':
                funcs[t] = v[1:]
            else:
                self._interpreter.define('_t_name', t)
                self._interpreter.define(t, v)
                self._interpreter.define('_t_name', t)

    def _eval_node(
        self, expr: Any, env: lisp_interpreter.Env
    ) -> tuple[bool, Any]:
        del env
        if isinstance(expr, m_grammar.Node):
            return True, expr
        return False, None

    def generate(self) -> str:
        obj = self._interpreter.eval(
            [['symbol', self.datafile['starting_template']]]
        )
        if self.options.generator_options.get('as_ll'):
            fmt_fn = formatter.flatten_as_lisplist
        else:
            fmt_fn = formatter.flatten
        lines = fmt_fn(obj, self.options.line_length, self.options.indent)
        return '\n'.join(lines) + '\n'

    def f_invoke(self, args, env) -> Any:
        """Invoke the template named in arg 1, passing it the remaining args."""
        first = self._interpreter.eval(args[0], env)
        obj = env.get(first)
        if not lisp_interpreter.is_fn(obj):
            return obj
        return self._interpreter.eval([['symbol', first]] + args[1:], env)
