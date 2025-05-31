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

import json
from typing import Any, Union

from pyfloyd import (
    at_exp,
    datafile,
    formatter,
    generator,
    grammar as m_grammar,
    lisp_interpreter,
    support,
)


DEFAULT_TEMPLATE = 'python.dft'

DEFAULT_LANGUAGE = DEFAULT_TEMPLATE[:-4]

KNOWN_TEMPLATES = {
    '.py': 'python',
    '.js': 'javascript',
}

KNOWN_LANGUAGES = {v: k for k, v in KNOWN_TEMPLATES.items()}


class DatafileGenerator(generator.Generator):
    name: str = 'datafile'
    help_str: str = 'Generate code from a datafile template'
    indent: Union[int, str] = 4
    line_length: int = 79

    def __init__(
        self,
        host: support.Host,
        data: dict['str', Any],
        options: generator.GeneratorOptions,
    ):
        # Do not pass the options to the base class; we want to
        # hold off on processing them until after we've loaded all
        # of the data.
        super().__init__(host, data, generator.GeneratorOptions())
        self._loaded_datafiles: set[str] = set()

        self._interpreter = interp = lisp_interpreter.Interpreter()
        interp.add_foreign_handler(self._eval_node)
        interp.define_native_fn('invoke', self.f_invoke)

        template = options.get('template', DEFAULT_TEMPLATE)
        if template is None:
            template = DEFAULT_TEMPLATE
        keys_to_merge = {'local_vars', 'templates'}
        if self.host.splitext(template)[1] == '':
            template = template + '.dft'
        self._load_datafile(template, keys_to_merge)

        self.grammar = self.data.grammar

        # Merge in the user-supplied generator options once all of the
        # templates and associated datafiles have been loaded; when set,
        # these override everything else.
        self._update_options(options)
        self.name = self.data.name
        self.ext = self.data.ext

        at_exp.bind_at_exps(interp, self.indent)
        for k, v in self.data.items():
            if k != 'templates':
                interp.env.set(k, v)
        self._process_templates()

        if self.data.grammar:
            if self.data.declare_local_vars:
                local_var_map = self.data.local_var_map
            else:
                local_var_map = {}
            self._process_grammar(local_var_map)

    def _load_datafile(self, name, keys_to_merge, as_template=True):
        if name in self._loaded_datafiles:
            return

        if name == '-':
            df_str = self.host.stdin.read()
            filename = '<stdin>'
        else:
            if self.host.exists(name):
                path = name
            else:
                path = self.host.join(self.host.dirname(__file__), name)
                if not self.host.exists(path):
                    raise ValueError(f"template file '{name}' not found")
            filename = self.host.relpath(path)
            df_str = self.host.read_text_file(path)

        if as_template:
            df = datafile.loads(
                df_str,
                parse_bareword=self._parse_bareword,
                custom_tags={'@': self._to_at_exp, 'q': self._to_quoted_list},
                filename=filename,
            )
        else:
            df = datafile.loads(df_str, filename=filename)

        self._loaded_datafiles.add(name)

        # Load definitions from any base templates; do this before
        # we process anything else in this file.
        if 'inherit' in df:
            for base in df['inherit']:
                if self.host.splitext(base)[1] == '':
                    base = base + '.dft'
                self._load_datafile(base, keys_to_merge)

        # Now load any data required by *this* datafile; it will overwrite
        # any data loaded from any previous datafiles.
        if 'datafiles' in self.data:
            for dataf in self.data.datafiles:
                if self.host.splitext(dataf)[1] == '':
                    dataf = dataf + '.df'
                self._load_datafile(dataf, keys_to_merge, as_template=False)

        # Lastly, merge the values defined in *this* datafile.
        self._merge_datafile(df, keys_to_merge)

    def _merge_datafile(self, df, keys_to_merge):
        if 'indent' in df and df['indent'] is not None:
            if isinstance(df['indent'], int):
                indent = df['indent'] * ' '
            else:
                indent = df['indent']
        else:
            indent = self.indent

        for df_key in df.keys():
            if df_key in self.data and df_key in keys_to_merge:
                for k, v in df[df_key].items():
                    if (
                        df_key == 'templates'
                        and isinstance(v, str)
                        and '\n' in v
                    ):
                        obj = formatter.split_to_objs(v, indent)
                    else:
                        obj = v
                    self.data[df_key][k] = obj
            else:
                self.data[df_key] = df[df_key]

    def _parse_bareword(self, s: str, as_key: bool) -> Any:
        if as_key:
            return s
        return ['symbol', s]

    def _to_at_exp(self, ty, tag, obj, as_key=False):
        assert ty == 'string' and tag == '@' and not as_key, (
            f'Uexpected tag fn invocation: '
            f'ty={ty} tag={tag} obj={repr(obj)}, as_key={as_key}'
        )
        s = datafile.dedent(obj[2], colno=obj[1])
        return [['symbol', 'fn'], [], [['symbol', 'at_exp'], s]]

    def _to_quoted_list(self, ty, tag, obj, as_key=False):
        assert ty == 'array' and tag == 'q' and not as_key, (
            f'Uexpected tag fn invocation: '
            f'ty={ty} tag={tag} obj={repr(obj)}, as_key={as_key}'
        )
        return [['symbol', 'quote'], obj]

    def _process_templates(self):
        data = self.data
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
        obj = self._interpreter.eval([['symbol', self.data.starting_template]])
        indent = self.indent
        assert isinstance(indent, str) and indent
        if self.options.as_json:
            return json.dumps(obj.to_list(), indent=indent)
        if self.options.output_as_format_tree:
            fmt_fn = formatter.flatten_as_lisplist
        else:
            fmt_fn = formatter.flatten
        lines = fmt_fn(obj, self.line_length, indent=indent)
        return '\n'.join(lines) + '\n'

    def f_invoke(self, args, env) -> Any:
        """Invoke the template named in arg 1, passing it the remaining args."""
        first = self._interpreter.eval(args[0], env)
        obj = env.get(first)
        if not lisp_interpreter.is_fn(obj):
            return obj
        return self._interpreter.eval([['symbol', first]] + args[1:], env)
