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

import collections
from typing import Any, Optional

from pyfloyd import custom_dicts
from pyfloyd import functions
from pyfloyd import type_desc


TD = type_desc.TypeDesc


class OperatorState:
    def __init__(self) -> None:
        # Map of precedence level to a list of operator literals that
        # have that level, e.g. {0: ['+'], 2: ['*']}
        self.prec_ops: dict[int, list[str]] = {}

        # Set of operator literals that are right-associative.
        self.rassoc: set[str] = set()

        # Map of operator literals to corresponding subrule names.
        self.choices: dict[str, str] = {}


BUILTIN_RULES = (
    'any',
    'end',
)


#
# AST node classes
#


class Node:
    def __init__(
        self,
        t: str,
        v: Any,
        ch: Optional[list['Node']] = None,
        parser: Any = None,
    ):
        self.t = t
        self.v = v
        self.ch: list['Node'] = ch or []
        assert isinstance(self.ch, list)
        self.type: Optional[TD] = None
        self.value_used: Optional[bool] = None
        self._can_fail: Optional[bool] = None
        self.memoize: Optional[bool] = None  # this will be set by a generator
        self.attrs = custom_dicts.AttrDict()
        if self.t == 'e_ident':
            self.attrs.outer_scope = False
            self.attrs.kind = ''  # 'extern', 'function', 'local', or 'outer'
        elif self.t == 'label':
            self.attrs.outer_scope = False
        elif self.t == 'leftrec':
            self.attrs.left_assoc = None
        elif self.t == 'seq':
            self.attrs.local_vars = {}
        elif self.t == 'rule':
            self.attrs.vars = {}
        self.parser = parser
        self.pos: Optional[int] = parser._pos if parser else None

    def __eq__(self, other) -> bool:
        assert isinstance(other, Node)
        return (
            self.t == other.t
            and self.v == other.v
            and self.ch == other.ch
            and self._can_fail == other._can_fail
        )

    def __repr__(self):
        return f'Node(t={self.t}, v={self.v}, ch={self.ch}, type={self.type})'

    @property
    def child(self):
        return self.ch[0]

    @child.setter
    def child(self, v):
        self.ch[0] = v

    @property
    def can_fail(self):
        assert self._can_fail is not None
        return self._can_fail

    @can_fail.setter
    def can_fail(self, flag: bool):
        self._can_fail = flag

    def can_fail_set(self) -> bool:
        return self._can_fail is not None

    def to_json(self, include_derived=False) -> Any:
        d: dict[str, Any] = {
            't': self.t,
        }
        if self.v is not None:
            d['v'] = self.v
        if self.ch:
            ch = [c.to_json(include_derived) for c in self.ch]
            d['ch'] = ch
        if self.type is not None:
            d['type'] = self.type
        if include_derived:
            d['can_fail'] = self.can_fail
            d['attrs'] = self.attrs
        return d

    def infer_types(self, g: 'Grammar', var_types: dict[str, TD]):
        if self.type is not None:
            return
        self.type = TD('any')  # TODO TD('wip')?

        if self.t != 'seq':
            for c in self.ch:
                c.infer_types(g, var_types)

        _fixed_types = {
            'e_getitem_infix': 'any',  # TODO: Figure out what this should be.
            'e_lit': 'str',
            'e_minus': 'int',
            'e_not': 'bool',
            'e_num': 'int',
            'e_plus': 'int',
            'empty': 'null',
            'equals': 'str',
            'leftrec': 'any',  # TODO: Figure out what this should be.
            'lit': 'str',
            'not': 'bool',
            'operator': 'any',  # TODO: Figure out what this should be.
            'range': 'str',
            'regexp': 'str',
            'rules': 'null',
            'run': 'str',
            'set': 'str',
            'unicat': 'str',
        }
        if self.t in _fixed_types:
            self.type = TD(_fixed_types[self.t])
        elif hasattr(self, '_infer_types_' + self.t):
            getattr(self, '_infer_types_' + self.t)(g, var_types)
        elif self.t in ('count', 'opt', 'plus', 'star'):
            self.type = TD('list', [self.child.type])
        else:
            # By default most nodes will have the type of the last of their
            # children, since that is also their default value.
            if self.ch:
                self.type = self.ch[-1].type

    def _infer_types_apply(self, g, var_types):
        if self.v in ('any', 'r_any'):
            self.type = TD('str')
        elif self.v in ('end', 'r_end'):
            self.type = TD('null')
        else:
            for n in g.ast.ch:
                if n.v == self.v:
                    n.infer_types(g, var_types)
                    self.type = n.type
                    return
            assert False

    def _infer_types_e_call_infix(self, g, var_types):
        del var_types
        assert self.ch[0].t == 'e_ident'
        if self.ch[0].v in g.externs and self.ch[0].v not in functions.ALL:
            self.type = TD('any')
            return

        assert self.ch[0].v in functions.ALL
        func_name = self.ch[0].v
        func = functions.ALL[func_name]
        params = func['params']
        if len(params) and params[-1][0].startswith('*'):
            last = len(params) - 1
            if len(self.ch[1:]) < last:
                g.errors.append(
                    f'{func_name}() takes at least {len(params)} '
                    f'args, got {len(self.ch[1:])}.'
                )
        else:
            last = len(params)
            if len(self.ch[1:]) != last:
                g.errors.append(
                    f'{func_name}() takes {len(params)} '
                    f'args, got {len(self.ch[1:])}.'
                )

        for i, c in enumerate(self.ch[1 : last + 1]):
            p_type = params[i][1]
            p_td = type_desc.from_str(p_type)
            assert c.type is not None
            if not type_desc.check_descs(p_td, c.type):
                g.errors.append(
                    f'Expected arg #{i + 1} to {func_name}() to be '
                    f'{p_type}, got {c.type.to_str()}.'
                )
        if last != len(params):
            p_type = params[last][1]
            p_td = type_desc.from_str(p_type)
            for i, c in enumerate(self.ch[last + 1 :]):
                assert c.type is not None
                if not type_desc.check_descs(p_td, c.type):
                    g.errors.append(
                        f'Expected arg #{last + 1 + i} to {func_name}() to be '
                        f'{p_type}, got {c.type.to_str()}.'
                    )
        self.type = TD(func['ret'])
        assert self.type is not None

    def _infer_types_choice(self, g, var_types):
        del g
        del var_types
        types = set()
        for c in self.ch:
            assert c.type is not None
            types.add(type_desc.d2str(c.type))
        self.type = TD(type_desc.merge(list(types)))

    def _infer_types_e_arr(self, g, var_types):
        del g
        del var_types
        types = []
        for c in self.ch:
            assert c.type is not None
            types.append(c.type)
        self.type = TD('tuple', types)

    def _infer_types_e_const(self, g, var_types):
        del g
        del var_types
        if self.v == 'null':
            self.type = TD('null')
        elif self.v == 'func':
            self.type = TD('func')
        else:
            self.type = TD('bool')

    def _infer_types_e_ident(self, g, var_types):
        if self.attrs.kind == 'function':
            self.type = TD('func')
        elif self.attrs.kind in ('local', 'outer'):
            self.type = var_types[self.v]
        else:
            assert self.attrs.kind == 'extern'
            if g.externs[self.v] == 'func':
                self.type = TD('func')
            else:
                self.type = TD('bool')

    def _infer_types_pred(self, g, var_types):
        del var_types
        if self.child.type['base'] != 'bool':
            g.errors.append('Non-bool object passed to `?{}`.')
        self.type = TD('bool')

    def _infer_types_rule(self, g, var_types):
        del g
        del var_types
        self.type = self.ch[-1].type
        assert self.type is not None
        if self.type['base'] == 'wip':
            self.type = TD('all')

    def _infer_types_seq(self, g: 'Grammar', var_types: dict[str, TD]):
        local_var_types = var_types.copy()
        for c in self.ch:
            c.infer_types(g, local_var_types)
            if c.t == 'label':
                assert c.type is not None
                local_var_types[c.v] = c.type
        self.type = self.ch[-1].type


class Grammar:
    def __init__(self, ast: Node):
        assert isinstance(ast, Node)
        self.ast = ast
        self.errors: list[str] = []
        self.comment: Optional[Node] = None
        self.rules: dict[str, Node] = collections.OrderedDict()
        self.pragmas: list[Node] = []
        self.starting_rule: str = ''
        self.tokens: set[str] = set()
        self.whitespace: Optional[Node] = None
        self.assoc: dict[str, str] = {}
        self.prec: dict[str, int] = {}
        self.exception_needed: bool = False
        self.leftrec_needed: bool = False
        self.lookup_needed: bool = False
        self.operator_needed: bool = False
        self.unicat_needed: bool = False
        self.ch_needed: bool = False
        self.str_needed: bool = False
        self.range_needed: bool = False
        self.re_needed: bool = False
        self.needed_builtin_functions: list[str] = []
        self.needed_builtin_rules: list[str] = []
        self.needed_operators: list[str] = [
            'error',
            'fail',
            'offsets',
            'rewind',
            'succeed',
        ]
        self.unicodedata_needed: bool = False
        self.seeds_needed: bool = False

        self.operators: dict[str, OperatorState] = {}
        self.leftrec_rules: set[str] = set()
        self.outer_scope_rules: set[str] = set()
        self.externs: dict[str, bool] = {}

        has_starting_rule = False
        for rule in self.ast.ch:
            if rule.v.startswith('%'):
                self.pragmas.append(rule)
            elif not has_starting_rule:
                self.starting_rule = rule.v
                has_starting_rule = True
            self.rules[rule.v] = rule.child

    def node(self, cls, *args, **kwargs) -> Node:
        n = cls(*args, **kwargs)
        return self.update_node(n)

    def update_node(self, node: Node) -> Node:
        self._set_can_fail(node)
        node.infer_types(self, var_types={})

        def _patch_types(node):
            if node.type['base'] == 'wip' and node.t == 'apply':
                node.type = self.rules[node.v].type
            for c in node.ch:
                _patch_types(c)

        _patch_types(node)

        node.infer_types(self, var_types={})

        return node

    def _set_can_fail(self, node):
        if node.can_fail_set():
            return
        for c in node.ch:
            self._set_can_fail(c)
        node.can_fail = self._can_fail(node)

    def update_rules(self):
        # Update grammar.rules to match grammar.ast for rules in
        # grammar.ast and then append any new rules to grammar.ast.
        rules = set()
        for rule in self.ast.ch:
            self.rules[rule.v] = rule.child
            rules.add(rule.v)
        for rule_name in self.rules:
            if rule_name not in rules:
                self.ast.ch.append(
                    Node('rule', rule_name, [self.rules[rule_name]])
                )

    # TODO: Figure out what to do with `inline`; it seems like there are
    # might be places where it's safe to ignore if something can fail if
    # inlined but not otherwise. See the commented-out lines below.
    def _can_fail(self, node: Node, inline: bool = True) -> bool:
        if node.can_fail_set():
            return node.can_fail
        if node.t in ('action', 'empty', 'opt', 'star'):
            return False
        if node.t == 'apply':
            if node.v in ('any', 'r_any', 'end', 'r_end'):
                return True
            # return self._can_fail(self.rules[node.v], inline=False)
            return self._can_fail(self.rules[node.v], inline)
        if node.t == 'label':
            # When the code for a label is being inlined, if the child
            # node can fail, its return will exit the outer method as well,
            # so we don't have to worry about it. At that point, then
            # we just have the label code itself, which can't fail.
            # When the code isn't being inlined into the outer method,
            # we do have to include the failure of the child node.
            # TODO: This same reasoning may be true for other types of nodes.
            # return False if inline else self._can_fail(node.child, inline)
            return self._can_fail(node.child, inline)
        if node.t in ('label', 'paren', 'rule', 'run'):
            return self._can_fail(node.child, inline)
        if node.t == 'count':
            return node.v[0] != 0
        if node.t in ('leftrec', 'operator', 'op'):
            # TODO: Figure out if there's a way to tell if these can not fail.
            return True
        if node.t in ('choice', 'rules'):
            r = all(self._can_fail(n, inline) for n in node.ch)
            return r
        if node.t == 'scope':
            # TODO: is this right?
            # return self._can_fail(node.ch[0], False)
            return self._can_fail(node.ch[0], inline)
        if node.t == 'seq':
            r = any(self._can_fail(n, inline) for n in node.ch)
            return r
        if node.t.startswith('e_'):
            return True

        # You might think that if a not's child node can fail, then
        # the not can't fail, but it doesn't work that way. If the
        # child == ['lit', 'foo'], then it'll fail if foo isn't next,
        # so it can fail, but ['not', [child]] can fail also (if
        # foo is next).
        # Note that some regexps might not fail, but to figure that
        # out we'd have to analyze the regexp itself, which I don't want to
        # do yet.
        assert node.t in (
            'ends_in',
            'equals',
            'lit',
            'not',
            'not_one',
            'plus',
            'pred',
            'range',
            'regexp',
            'set',
            'unicat',
        )

        return True
