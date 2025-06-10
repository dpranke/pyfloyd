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

from typing import Any, Union

from pyfloyd import (
    datafile,
    generator,
    grammar as m_grammar,
    formatter,
    string_literal,
    support,
)


class HardCodedGenerator(generator.Generator):
    def __init__(
        self,
        host: support.Host,
        data: dict[str, Any],
        options: generator.GeneratorOptions,
    ):
        super().__init__(host, data, options)
        # Expected to be overridden in subclasses
        self._map: dict[str, str] = {}
        self._builtin_methods: dict[str, str] = {}

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

    def generate(self) -> str:
        raise NotImplementedError

    def _gen_extern(self, name: str) -> str:
        raise NotImplementedError

    def _gen_invoke(self, fn: str, *args) -> formatter.FormatObj:
        raise NotImplementedError

    def _gen_funcname(self, name: str) -> str:
        raise NotImplementedError

    def _gen_thisvar(self, name: str) -> str:
        raise NotImplementedError

    def _gen_rulename(self, name: str) -> str:
        raise NotImplementedError

    def _gen_varname(self, name: str) -> str:
        r = f'v_{name.replace("$", "_")}'
        return r

    def _gen_opname(self, name: str) -> str:
        raise NotImplementedError

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
        assert isinstance(node, m_grammar.Apply)
        if node.memoize:
            return formatter.HList(
                self._gen_invoke(
                    self._gen_opname('memoize'),
                    f"'{node.rule_name}'",
                    self._gen_rulename(node.rule_name),
                ),
                self._map['end'],
            )
        return formatter.HList(
            self._gen_invoke(node.rule_name), self._map['end']
        )

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
        if node.ch[0][1] in self.grammar.externs:
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
        assert isinstance(node, m_grammar.EMinus)
        return formatter.Tree(
            self._gen_expr(node.left), '-', self._gen_expr(node.right)
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
        assert isinstance(node, m_grammar.EPlus)
        return formatter.Tree(
            self._gen_expr(node.left), '+', self._gen_expr(node.right)
        )

    def _ty_e_qual(self, node: m_grammar.Node) -> formatter.Pack:
        # e_{call,getitem,qual} have been rewritten to e_{call,getitem}_infix.
        del node
        assert False, '`e_qual` should never be invoked'

    def _ty_e_ident(self, node: m_grammar.Node) -> formatter.El:
        assert isinstance(node, m_grammar.EIdent)
        if node.kind == 'outer':
            return self._gen_invoke(
                self._gen_opname('lookup'), "'" + node.v + "'"
            )
        if node.kind == 'extern':
            return self._gen_extern(node.v)
        if node.kind == 'function':
            return self._gen_funcname(node.v)
        assert node.kind == 'local', f'Unexpected identifer kind {node!r}'
        return self._gen_varname(node.v)

    def _ty_empty(self, node) -> formatter.FormatObj:
        del node
        return formatter.HList(
            self._gen_invoke(self._gen_opname('succeed'), self._map['null']),
            self._map['end'],
        )

    def _ty_equals(self, node) -> formatter.FormatObj:
        arg = self._gen_expr(node.child)
        return formatter.HList(
            self._gen_invoke(self._gen_opname('str'), arg), self._map['end']
        )

    def _ty_leftrec(self, node) -> formatter.FormatObj:
        if node.left_assoc:
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

    def _ty_operator(self, node) -> formatter.FormatObj:
        # Operator nodes have no children, but subrules for each arm
        # of the expression cluster have been defined and are referenced
        # from self.grammar.operators[node.v].choices.
        assert node.ch == []
        return formatter.HList(
            self._gen_invoke(self._gen_opname('operator'), "'" + node.v + "'"),
            self._map['end'],
        )

    def _ty_range(self, node) -> formatter.FormatObj:
        return formatter.HList(
            self._gen_invoke(
                self._gen_opname('range'),
                self._gen_lit(node.start),
                self._gen_lit(node.stop),
            ),
            self._map['end'],
        )

    def _ty_regexp(self, node) -> formatter.FormatObj:
        raise NotImplementedError

    def _ty_set(self, node) -> formatter.FormatObj:
        new_node = m_grammar.Regexp('[' + node.v + ']')
        return self._ty_regexp(new_node)

    def _ty_unicat(self, node) -> formatter.FormatObj:
        return formatter.HList(
            self._gen_invoke(
                self._gen_opname('unicat'), self._gen_lit(node.v)
            ),
            self._map['end'],
        )
