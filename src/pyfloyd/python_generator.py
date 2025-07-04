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

from typing import Any, Optional, Union

from pyfloyd import (
    datafile,
    formatter,
    generator,
    grammar as m_grammar,
    string_literal,
    support,
)


class PythonGenerator(generator.Generator):
    name: str = 'Python'
    ext: str = '.py'
    indent: Union[int, str] = 4
    line_length: Optional[int] = 79

    def __init__(
        self,
        host: support.Host,
        data: dict[str, Any],
        options: generator.GeneratorOptions,
    ):
        assert 'grammar' in data
        super().__init__(host, data, options)
        self._map = {
            'end': '',
            'false': 'False',
            'indent': '    ',
            'Infinity': "float('inf')",
            'NaN': "float('NaN')",
            'not': 'not ',
            'null': 'None',
            'true': 'True',
        }

        self._builtin_methods = {}
        for k, v in _BUILTINS.items():
            self._builtin_methods[k] = datafile.dedent(v)

        # Python doesn't need to declare local vars.
        self._process_grammar(local_var_map={})

    def _defmt(self, s: str, dedented=False) -> formatter.VList:
        if dedented:
            text = s
        else:
            text = datafile.dedent(s)
        vl = formatter.VList()
        lines = text.splitlines()
        for line in lines:
            vl += line
        return vl

    def _defmtf(self, s: str, dedented=False, **kwargs) -> formatter.VList:
        if dedented:
            text = s
        else:
            text = datafile.dedent(s)
        lines = text.format(**kwargs).splitlines()
        vl = formatter.VList()
        for line in lines:
            vl += line
        return vl

    def _fmt(self, obj: formatter.FormatObj) -> str:
        indent = self.indent
        assert isinstance(indent, str) and indent
        text = '\n'.join(formatter.flatten(obj, indent=indent)) + '\n'
        return text

    def _gen_varname(self, name: str) -> str:
        r = f'v_{name.replace("$", "_")}'
        return r

    def _gen_lit(self, lit: str) -> str:
        return string_literal.encode(lit)

    def _gen_expr(self, node: m_grammar.Node) -> formatter.FormatObj:
        fn = getattr(self, f'_ty_{node.t}')
        return fn(node)

    def _gen_stmts(self, node: m_grammar.Node) -> formatter.VList:
        fn = getattr(self, f'_ty_{node.t}')
        r = fn(node)
        if not isinstance(r, formatter.VList):
            r = formatter.VList(r)
        return r

    def _gen_needed_methods(self) -> formatter.FormatObj:
        obj = formatter.VList()

        def add_method(name: str):
            nonlocal obj
            obj += ''
            obj += self._defmt(self._builtin_methods[name], dedented=True)

        if self.grammar.ch_needed:
            add_method('ch')
        add_method('error')
        add_method('fail')
        if self.grammar.leftrec_needed:
            add_method('leftrec')
        if self.grammar.lookup_needed:
            add_method('lookup')
        if self.options.memoize:
            add_method('memoize')
        add_method('offsets')
        if self.grammar.operator_needed:
            add_method('operator')
        if self.grammar.range_needed:
            add_method('range')
        add_method('rewind')
        if self.grammar.str_needed:
            add_method('str')
        add_method('succeed')
        if self.grammar.unicat_needed:
            add_method('unicat')
        return obj

    def generate(self) -> str:
        vl = formatter.VList()
        if self.options.main:
            vl += self._gen_main_header(
                self.options.version, self.options.command_line
            )
        else:
            vl += self._gen_default_header(
                self.options.version, self.options.command_line
            )

        if self.grammar.exception_needed:
            vl += ''
            vl += ''
            vl += self._gen_parsing_runtime_exception_class()

        if self.grammar.operators:
            vl += ''
            vl += ''
            vl += self._gen_operator_state_class()

        vl += ''
        vl += ''
        vl += self._gen_result_class()
        vl += ''
        vl += ''
        vl += self._gen_parse_function()
        vl += ''
        vl += ''
        vl += self._gen_parser_class()

        if self.options.main:
            vl += self._gen_main_footer()
        else:
            vl += self._gen_default_footer()
        return self._fmt(vl)

    def _gen_main_header(self, version, args) -> formatter.FormatObj:
        imports = self._fmt(self._gen_imports())
        return self._defmtf(
            """
            #!/usr/bin/env python3
            #
            # Generated by pyfloyd version {version}
            #    https://github.com/dpranke/pyfloyd
            #    `pyfloyd {args}`

            {imports}

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
                arg_parser.add_argument('-c', '--code')
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

                if args.code is not None:
                    msg = args.code
                    path = '<code>'
                elif not args.file or args.file[1] == '-':
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

                if args.code is None:
                    msg = fp.read()
                result = parse(msg, path, externs)
                if result.err:
                    print(result.err, file=stderr)
                    return 1
                print(json.dumps(result.val, indent=2), file=stdout)
                return 0
            """,
            imports=imports,
            args=args,
            version=version,
        )

    def _gen_default_header(self, version, args) -> formatter.FormatObj:
        imports = self._fmt(self._gen_imports())
        return self._defmtf(
            """
            # Generated by pyfloyd version {version}
            #    https://github.com/dpranke/pyfloyd
            #    `pyfloyd {args}`

            {imports}

            Externs = Optional[Dict[str, Any]]

            # pylint: disable=too-many-lines
            """,
            imports=imports,
            version=version,
            args=args,
        )

    def _gen_imports(self) -> formatter.FormatObj:
        vl = formatter.VList()
        if self.options.main:
            vl += 'import argparse'
        if self.options.main:
            vl += 'import json'
            vl += 'import os'
        if self.grammar.re_needed:
            vl += 'import re'
        if self.options.main:
            vl += 'import sys'
        vl += 'from typing import Any, Dict, NamedTuple, Optional'
        if self.options.unicodedata_needed:
            vl += 'import unicodedata'
        return vl

    def _gen_parsing_runtime_exception_class(self) -> formatter.FormatObj:
        return self._defmt("""
            class _ParsingRuntimeError(Exception):
                pass
            """)

    def _gen_operator_state_class(self) -> formatter.FormatObj:
        return self._defmt("""
            class _OperatorState:
                def __init__(self):
                    self.current_depth = 0
                    self.current_prec = 0
                    self.prec_ops = {}
                    self.precs = []
                    self.rassoc = set()
                    self.choices = {}
            """)

    def _gen_result_class(self) -> formatter.FormatObj:
        return self._defmt("""
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
            """)

    def _gen_parse_function(self) -> formatter.FormatObj:
        return self._defmt("""
            def parse(
                text: str, path: str = '<string>', externs: Externs = None, start: int = 0
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
                return _Parser(text, path).parse(externs, start)
            """)

    def _gen_parser_class(self) -> formatter.FormatObj:
        vl = self._defmt("""
            class _Parser:
            """)

        methods = self._gen_constructor()
        methods += ''
        methods += self._gen_methods()
        vl += formatter.Indent(methods)
        return vl

    def _gen_constructor(self) -> formatter.VList:
        obj = formatter.VList('def __init__(self, text, path):')

        vl = self._defmt("""
            self._text = text
            self._end = len(self._text)
            self._errpos = 0
            self._failed = False
            self._path = path
            self._pos = 0
            self._val = None
            """)

        if self.grammar.externs:
            vl += 'self._externs = {'
            for k, v in self.grammar.externs.items():
                if v in ('func', 'pfunc'):
                    vl += f"    '{k}': self._fn_{k},"
                else:
                    vl += f"    '{k}': {v},"
            vl += '}'
        else:
            vl += 'self._externs = {}'

        if self.options.memoize:
            vl += 'self._cache = {}'
        if self.grammar.leftrec_needed or self.grammar.operator_needed:
            vl += 'self._seeds = {}'
        if self.grammar.leftrec_needed:
            vl += 'self._blocked = set()'
        if self.grammar.re_needed:
            vl += 'self._regexps = {}'
        if self.grammar.lookup_needed:
            vl += 'self._scopes = []'
        if self.grammar.operator_needed:
            vl += self._gen_operator_state()
        obj += formatter.Indent(vl)
        return obj

    def _gen_operator_state(self) -> formatter.FormatObj:
        vl = formatter.VList()
        vl += 'self._operators = {}'
        for rule, o in self.grammar.operators.items():
            vl += 'o = _OperatorState()'
            vl += 'o.prec_ops = {'
            text = ''
            for prec in sorted(o.prec_ops):
                text += '    ' + str(prec) + ': ['
                text += ', '.join("'" + op + "'" for op in o.prec_ops[prec])
                text += '],\n'
            vl += formatter.Indent(formatter.VList(*text.splitlines()))
            vl += '}'
            vl += 'o.precs = sorted(o.prec_ops, reverse=True)'
            vl += (
                'o.rassoc = set(['
                + ', '.join("'" + op + "'" for op in o.rassoc)
                + '])'
            )
            vl += 'o.choices = {'
            choices = formatter.VList()
            for op in o.choices:
                choices += "'" + op + "': self._" + o.choices[op] + ','
            vl += formatter.Indent(choices)
            vl += '}'
            vl += "self._operators['" + rule + "'] = o"
        return vl

    def _gen_methods(self) -> formatter.FormatObj:
        vobj = formatter.VList()
        vobj += self._gen_parse_method(
            exception_needed=self.grammar.exception_needed,
            starting_rule=self.grammar.starting_rule,
        )

        vobj += self._gen_rule_methods()

        vobj += self._gen_needed_methods()

        for name in self.grammar.needed_builtin_functions:
            vobj += ''
            vobj += self._defmt(
                self._builtin_methods[f'fn_{name}'], dedented=True
            )

        return vobj

    def _gen_parse_method(
        self, exception_needed, starting_rule
    ) -> formatter.VList:
        if exception_needed:
            return self._defmt(
                f"""
                def parse(self, externs: Externs = None, start: int = 0):
                    self._pos = start

                    errors = ''
                    if externs:
                        for k, v in externs.items():
                            if k in self._externs:
                                self._externs[k] = v
                            else:
                                errors += f'Unexpected extern "{{k}}"\\n'
                    for k, v in self._externs.items():
                        if v is None:
                            errors += f'Missing required extern "{{k}}"\\n'

                    if errors:
                        return Result(None, errors, 0)
                    try:
                        self._r_{starting_rule}()

                        if self._failed:
                            return Result(None, self._o_error(), self._errpos)
                        return Result(self._val, None, self._pos)
                    except _ParsingRuntimeError as e:  # pragma: no cover
                        lineno, _ = self._o_offsets(self._errpos)
                        return Result(
                            None,
                            self._path + ':' + str(lineno) + ' ' + str(e),
                            self._errpos,
                        )
                """
            )
        return self._defmt(
            f"""
            def parse(self, externs: Externs = None, start: int = 0):
                self._pos = start
                if externs:
                    for k, v in externs.items():
                        self._externs[k] = v

                self._r_{starting_rule}()

                if self._failed:
                    return Result(None, self._o_error(), self._errpos)
                return Result(self._val, None, self._pos)
            """
        )

    def _gen_rule_methods(self) -> formatter.VList:
        obj = formatter.VList()
        for rule, node in self.grammar.rules.items():
            obj += ''
            obj += self._gen_method_text(rule, node)

        if self.grammar.needed_builtin_rules:
            for name in sorted(self.grammar.needed_builtin_rules):
                obj += ''
                obj += self._defmt(
                    self._builtin_methods[f'r_{name}'], dedented=True
                )
        return obj

    def _gen_method_text(
        self, method_name: str, node: m_grammar.Node
    ) -> formatter.VList:
        return formatter.VList(
            formatter.HList('def _', method_name, '(self):'),
            formatter.Indent(self._gen_stmts(node)),
        )

    def _gen_thisvar(self, name: str) -> str:
        return 'self._' + name

    def _gen_rulename(self, name: str) -> str:
        return 'self._' + name

    def _gen_funcname(self, name: str) -> str:
        return 'self._fn_' + name

    def _gen_extern(self, name: str) -> str:
        return "self._externs['" + name + "']"

    def _gen_opname(self, name: str) -> str:
        return 'o_' + name

    def _gen_invoke(self, fn, *args) -> formatter.Pack:
        return formatter.Pack(
            'self._' + fn, formatter.Triangle('(', formatter.Comma(*args), ')')
        )

    def _gen_main_footer(self) -> formatter.VList:
        return self._defmt("""


            if __name__ == '__main__':
                sys.exit(main())
            """)

    def _gen_default_footer(self) -> formatter.VList:
        return formatter.VList()

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _ty_action(self, node: m_grammar.Node) -> formatter.FormatObj:
        return formatter.HList(
            self._gen_invoke(
                self._gen_opname('succeed'), self._gen_expr(node.child)
            ),
            self._map['end'],
        )

    def _ty_apply(self, node: m_grammar.Node) -> formatter.FormatObj:
        if node.memoize:
            return formatter.HList(
                self._gen_invoke(
                    self._gen_opname('memoize'),
                    f"'{node.v}'",
                    self._gen_rulename(node.v),
                ),
                self._map['end'],
            )
        return formatter.HList(self._gen_invoke(node.v), self._map['end'])

    def _ty_choice(self, node: m_grammar.Node) -> formatter.FormatObj:
        vl = formatter.VList('p = self._pos')
        for subnode in node.ch[:-1]:
            vl += self._gen_stmts(subnode)
            vl += 'if not self._failed:'
            vl += '    return'
            vl += 'self._o_rewind(p)'
        vl += self._gen_stmts(node.ch[-1])
        return vl

    def _ty_count(self, node: m_grammar.Node) -> formatter.FormatObj:
        vl = formatter.VList(
            'vs = []',
            'i = 0',
            f'cmin, cmax = {node.v}',
            'while i < cmax:',
        )
        svl = self._gen_stmts(node.child)
        svl += 'if self._failed:'
        svl += '    if i >= cmin:'
        svl += '        self._o_succeed(vs)'
        svl += '        return'
        svl += '    return'
        svl += 'vs.append(self._val)'
        svl += 'i += 1'

        vl += formatter.Indent(svl)
        vl += 'self._o_succeed(vs)'
        return vl

    def _ty_e_arr(
        self, node: m_grammar.Node
    ) -> Union[str, formatter.Triangle]:
        if len(node.ch) == 0:
            return '[]'
        args = [self._gen_expr(c) for c in node.ch]
        return formatter.Triangle('[', formatter.Comma(*args), ']')

    def _ty_e_call(self, node: m_grammar.Node) -> formatter.Triangle:
        # e_{call,getitem,qual} have been rewritten to e_{call,getitem}_infix.
        del node
        assert False, '`e_call` should never be invoked'

    def _ty_e_call_infix(self, node: m_grammar.Node) -> formatter.Pack:
        pfx = self._gen_expr(node.ch[0])
        args = [self._gen_expr(c) for c in node.ch[1:]]
        fname = node.ch[0].v
        if self.grammar.externs.get(fname) == 'pfunc':
            return formatter.Pack(
                pfx,
                formatter.Triangle('(', formatter.Comma('self', *args), ')'),
            )
        return formatter.Pack(
            pfx, formatter.Triangle('(', formatter.Comma(*args), ')')
        )

    def _ty_e_const(self, node: m_grammar.Node) -> str:
        assert isinstance(node.v, str)
        return self._map[node.v]

    def _ty_e_getitem(self, node: m_grammar.Node) -> formatter.Triangle:
        # e_{call,getitem,qual} have been rewritten to e_{call,getitem}_infix.
        del node
        assert False, '`e_getitem` should never be invoked'

    def _ty_e_getitem_infix(self, node: m_grammar.Node) -> formatter.HList:
        return formatter.HList(
            self._gen_expr(node.ch[0]),
            formatter.Triangle('[', self._gen_expr(node.ch[1]), ']'),
        )

    def _ty_e_lit(self, node: m_grammar.Node) -> str:
        return self._gen_lit(node.v)

    def _ty_e_minus(self, node: m_grammar.Node) -> formatter.Tree:
        return formatter.Tree(
            self._gen_expr(node.ch[0]), '-', self._gen_expr(node.ch[1])
        )

    def _ty_e_not(self, node: m_grammar.Node) -> formatter.Tree:
        return formatter.Tree(
            None, self._map['not'], self._gen_expr(node.child)
        )

    def _ty_e_num(self, node: m_grammar.Node) -> str:
        assert isinstance(node.v, str)
        return str(node.v)

    def _ty_e_paren(self, node: m_grammar.Node) -> formatter.FormatObj:
        return self._gen_expr(node.child)

    def _ty_e_plus(self, node: m_grammar.Node) -> formatter.Tree:
        return formatter.Tree(
            self._gen_expr(node.ch[0]), '+', self._gen_expr(node.ch[1])
        )

    def _ty_e_qual(self, node: m_grammar.Node) -> formatter.Pack:
        # e_{call,getitem,qual} have been rewritten to e_{call,getitem}_infix.
        del node
        assert False, '`e_qual` should never be invoked'

    def _ty_e_ident(self, node: m_grammar.Node) -> formatter.El:
        if node.attrs.kind == 'outer':
            return self._gen_invoke(
                self._gen_opname('lookup'), "'" + node.v + "'"
            )
        if node.attrs.kind == 'extern':
            return self._gen_extern(node.v)
        if node.attrs.kind == 'function':
            return self._gen_funcname(node.v)
        assert node.attrs.kind == 'local', (
            f'Unexpected identifer kind {node!r}'
        )
        return self._gen_varname(node.v)

    def _ty_empty(self, node) -> formatter.FormatObj:
        del node
        return formatter.HList(
            self._gen_invoke(self._gen_opname('succeed'), self._map['null']),
            self._map['end'],
        )

    def _ty_ends_in(self, node: m_grammar.Node) -> formatter.FormatObj:
        vl = formatter.VList('while True:')
        vl += formatter.Indent(self._gen_stmts(node.child))
        if node.can_fail:
            vl += ['    if not self._failed:', '        break']
        vl += [
            '    self._r_any()',
            '    if self._failed:',
            '        break',
        ]
        return vl

    def _ty_equals(self, node) -> formatter.FormatObj:
        arg = self._gen_expr(node.child)
        return formatter.HList(
            self._gen_invoke(self._gen_opname('str'), arg), self._map['end']
        )

    def _ty_label(self, node: m_grammar.Node) -> formatter.FormatObj:
        vl = formatter.VList(self._gen_stmts(node.child))
        if node.child.can_fail:
            vl += ['if self._failed:', '    return']
        if node.attrs.outer_scope:
            vl += f"self._scopes[-1]['{node.v}'] = self._val"
        else:
            vl += f'{self._gen_varname(node.v)} = self._val'
        return vl

    def _ty_leftrec(self, node) -> formatter.FormatObj:
        if node.attrs.left_assoc:
            left_assoc = self._map['true']
        else:
            left_assoc = self._map['false']

        return formatter.HList(
            self._gen_invoke(
                self._gen_opname('leftrec'),
                self._gen_rulename(node.child.v),
                "'" + node.v + "'",
                left_assoc,
            ),
            self._map['end'],
        )

    def _ty_lit(self, node) -> formatter.FormatObj:
        expr = self._gen_lit(node.v)
        if len(node.v) == 1:
            method = 'o_ch'
        else:
            method = 'o_str'
        return formatter.HList(
            self._gen_invoke(method, expr), self._map['end']
        )

    def _ty_not(self, node: m_grammar.Node) -> formatter.FormatObj:
        vl = formatter.VList(
            'p = self._pos',
            'errpos = self._errpos',
        )
        vl += self._gen_stmts(node.child)
        vl += [
            'if self._failed:',
            '    self._o_succeed(None, p)',
            'else:',
            '    self._o_rewind(p)',
            '    self._errpos = errpos',
            '    self._o_fail()',
        ]
        return vl

    def _ty_not_one(self, node: m_grammar.Node) -> formatter.FormatObj:
        sublines = self._gen_stmts(m_grammar.Node('not', None, [node.child]))
        vl = formatter.VList()
        vl += sublines
        vl += ['if not self._failed:', '    self._r_any()']
        return vl

    def _ty_operator(self, node) -> formatter.FormatObj:
        # Operator nodes have no children, but subrules for each arm
        # of the expression cluster have been defined and are referenced
        # from self.grammar.operators[node.v].choices.
        assert node.ch == []
        return formatter.HList(
            self._gen_invoke(self._gen_opname('operator'), "'" + node.v + "'"),
            self._map['end'],
        )

    def _ty_opt(self, node: m_grammar.Node) -> formatter.FormatObj:
        vl = formatter.VList('p = self._pos')
        vl += self._gen_stmts(node.child)
        vl += [
            'if self._failed:',
            '    self._o_succeed([], p)',
            'else:',
            '    self._o_succeed([self._val])',
        ]
        return vl

    def _ty_paren(self, node: m_grammar.Node) -> formatter.FormatObj:
        return self._gen_stmts(node.child)

    def _ty_plus(self, node: m_grammar.Node) -> formatter.FormatObj:
        sublines = self._gen_stmts(node.child)
        vl = formatter.VList('vs = []')
        vl += sublines
        vl += [
            'if self._failed:',
            '    return',
            'vs.append(self._val)',
            'while True:',
            '    p = self._pos',
            formatter.Indent(sublines),
            '    if self._failed or self._pos == p:',
            '        self._o_rewind(p)',
            '        break',
            '    vs.append(self._val)',
            'self._o_succeed(vs)',
        ]
        return vl

    def _ty_pred(self, node: m_grammar.Node) -> formatter.FormatObj:
        arg = self._gen_expr(node.child)
        return formatter.VList(
            formatter.HList('v = ', arg),
            'if v is True:',
            '    self._o_succeed(v)',
            'elif v is False:',
            '    self._o_fail()',
            'else:',
            "    raise _ParsingRuntimeError('Bad predicate value')",
        )

    def _ty_regexp(self, node: m_grammar.Node) -> formatter.FormatObj:
        return formatter.VList(
            f'p = {self._gen_lit(node.v)}',
            'if p not in self._regexps:',
            '    self._regexps[p] = re.compile(p)',
            'm = self._regexps[p].match(self._text, self._pos)',
            'if m:',
            '    self._o_succeed(m.group(0), m.end())',
            '    return',
            'self._o_fail()',
        )

    def _ty_run(self, node: m_grammar.Node) -> formatter.VList:
        vl = formatter.VList('start = self._pos')
        vl += self._gen_stmts(node.child)
        if node.child.can_fail:
            vl += ['if self._failed:', '    return']
        vl += [
            'end = self._pos',
            'self._val = self._text[start:end]',
        ]
        return vl

    def _ty_scope(self, node: m_grammar.Node) -> formatter.VList:
        vl = formatter.VList('self._scopes.append({})')
        vl += self._gen_stmts(node.child)
        vl += 'self._scopes.pop()'
        return vl

    def _ty_range(self, node) -> formatter.FormatObj:
        return formatter.HList(
            self._gen_invoke(
                self._gen_opname('range'),
                self._gen_lit(node.v[0]),
                self._gen_lit(node.v[1]),
            ),
            self._map['end'],
        )

    def _ty_seq(self, node: m_grammar.Node) -> formatter.VList:
        vl = formatter.VList(self._gen_stmts(node.ch[0]))
        if node.ch[0].can_fail:
            vl += ['if self._failed:', '    return']
        for subnode in node.ch[1:-1]:
            vl += self._gen_stmts(subnode)
            if subnode.can_fail:
                vl += ['if self._failed:', '    return']
        vl += self._gen_stmts(node.ch[-1])
        return vl

    def _ty_set(self, node) -> formatter.FormatObj:
        new_node = m_grammar.Node('regexp', '[' + node.v + ']', [])
        return self._ty_regexp(new_node)

    def _ty_star(self, node: m_grammar.Node) -> formatter.VList:
        sublines = self._gen_stmts(node.child)
        vl = formatter.VList(
            'vs = []',
            'while True:',
            '    p = self._pos',
        )
        vl += formatter.Indent(sublines)
        vl += [
            '    if self._failed or self._pos == p:',
            '        self._o_rewind(p)',
            '        break',
            '    vs.append(self._val)',
            'self._o_succeed(vs)',
        ]
        return vl

    def _ty_unicat(self, node) -> formatter.FormatObj:
        return formatter.HList(
            self._gen_invoke(
                self._gen_opname('unicat'), self._gen_lit(node.v)
            ),
            self._map['end'],
        )


_BUILTINS = {
    'r_any': """
        def _r_any(self):
            if self._pos < self._end:
                self._o_succeed(self._text[self._pos], self._pos + 1)
            else:
                self._o_fail()
        """,
    'r_end': """
        def _r_end(self):
            if self._pos == self._end:
                self._o_succeed(None)
            else:
                self._o_fail()
        """,
    'ch': """
        def _o_ch(self, ch):
            p = self._pos
            if p < self._end and self._text[p] == ch:
                self._o_succeed(ch, self._pos + 1)
            else:
                self._o_fail()
        """,
    'offsets': """
        def _o_offsets(self, pos):
            lineno = 1
            colno = 1
            for i in range(pos):
                if self._text[i] == '\\n':
                    lineno += 1
                    colno = 1
                else:
                    colno += 1
            return lineno, colno
        """,
    'error': """
        def _o_error(self):
            lineno, colno = self._o_offsets(self._errpos)
            if self._errpos == len(self._text):
                thing = 'end of input'
            else:
                thing = repr(self._text[self._errpos]).replace("'", '"')
            path = self._path
            return f'{path}:{lineno} Unexpected {thing} at column {colno}'
        """,
    'fail': """
        def _o_fail(self):
            self._val = None
            self._failed = True
            self._errpos = max(self._errpos, self._pos)
        """,
    'leftrec': """
        def _o_leftrec(self, rule, rule_name, left_assoc):
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
        """,
    'lookup': """
        def _o_lookup(self, var):
            i = len(self._scopes) - 1
            while i >= 0:
                if var in self._scopes[i]:
                    return self._scopes[i][var]
                i -= 1
            if var in self._externs:
                return self._externs[var]
            assert False, f'unknown var {var}'
        """,
    'memoize': """
        def _o_memoize(self, rule_name, fn):
            p = self._pos
            r = self._cache.setdefault(p, {}).get(rule_name)
            if r:
                self._val, self._failed, self._pos = r
                return
            fn()
            self._cache[p][rule_name] = (self._val, self._failed, self._pos)
        """,
    'operator': """
        def _o_operator(self, rule_name):
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
                    self._o_rewind(pos)
                if not repeat:
                    i += 1

            del self._seeds[key]
            o.current_depth -= 1
            if o.current_depth == 0:
                o.current_prec = 0
            self._val, self._failed, self._pos = current
        """,
    'range': """
        def _o_range(self, i, j):
            p = self._pos
            if p != self._end and ord(i) <= ord(self._text[p]) <= ord(j):
                self._o_succeed(self._text[p], self._pos + 1)
            else:
                self._o_fail()
        """,
    'rewind': """
        def _o_rewind(self, newpos):
            self._o_succeed(None, newpos)
        """,
    'str': """
        def _o_str(self, s):
            for ch in s:
                self._o_ch(ch)
                if self._failed:
                    return
            self._val = s
        """,
    'succeed': """
        def _o_succeed(self, v, newpos=None):
            self._val = v
            self._failed = False
            if newpos is not None:
                self._pos = newpos
        """,
    'unicat': """
        def _o_unicat(self, cat):
            p = self._pos
            if p < self._end and unicodedata.category(self._text[p]) == cat:
                self._o_succeed(self._text[p], self._pos + 1)
            else:
                self._o_fail()
        """,
    'fn_atof': """
        def _fn_atof(self, s):
            if '.' in s or 'e' in s or 'E' in s:
                return float(s)
            return int(s)
        """,
    'fn_atoi': """
        def _fn_atoi(self, a, base):
            return int(a, base)
        """,
    'fn_atou': """
        def _fn_atou(self, a, base):
            return chr(int(a, base))
        """,
    'fn_cat': """
        def _fn_cat(self, strs):
            return ''.join(strs)
        """,
    'fn_colno': """
        def _fn_colno(self):
            colno = 0
            if self._pos == self._end:
                colno += 1
            while self._pos >= colno and self._text[self._pos - colno] != '\\n':
                colno += 1
            return colno
        """,
    'fn_concat': """
        def _fn_concat(self, xs, ys):
            return xs + ys
        """,
    'fn_cons': """
        def _fn_cons(self, hd, tl):
            return [hd] + tl
        """,
    'fn_dedent': """
        def _fn_dedent(self, s, colno, min_indent):
            return s
        """,
    'fn_dict': """
        def _fn_dict(self, pairs):
            return dict(pairs)
        """,
    'fn_itou': """
        def _fn_itou(self, n):
            return chr(n)
        """,
    'fn_join': """
        def _fn_join(self, s, vs):
            return s.join(vs)
        """,
    'fn_list': """
        def _fn_list(self, *args):
            return list(args)
        """,
    'fn_node': """
        def _fn_node(self, parser, *args):
            return args[0]
        """,
    'fn_otou': """
        def _fn_otou(self, s):
            return chr(int(s, base=8))
        """,
    'fn_pos': """
        def _fn_pos(self):
            return self._pos
        """,
    'fn_scat': """
        def _fn_scat(self, hd, tl):
            return self._fn_cat(self._fn_cons(hd, tl))
        """,
    'fn_scons': """
        def _fn_scons(self, hd, tl):
            return [hd] + tl
        """,
    'fn_strcat': """
        def _fn_strcat(self, a, b):
            return a + b
        """,
    'fn_ulookup': """
        def _fn_ulookup(self, s):
            return unicodedata.lookup(s)
        """,
    'fn_unicode_lookup': """
        def _fn_unicode_lookup(self, s):
            return unicodedata.lookup(s)
        """,
    'fn_utoi': """
        def _fn_utoi(self, s):
            return ord(s)
        """,
    'fn_xtoi': """
        def _fn_xtoi(self, s):
            return int(s, base=16)
        """,
    'fn_xtou': """
        def _fn_xtou(self, s):
            return chr(int(s, base=16))
        """,
}
