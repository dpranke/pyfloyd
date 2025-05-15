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
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class OperatorState:
    def __init__(self):
        # Map of precedence level to a list of operator literals that
        # have that level, e.g. {0: ['+'], 2: ['*']}
        self.prec_ops = {}  # Dict[int, List[str]]

        # Set of operator literals that are right-associative.
        self.rassoc = set()  # Set[str]

        # Map of operator literals to corresponding subrule names.
        self.choices = {}  # Dict[str, str]


class Grammar:
    def __init__(self, ast: Any):
        self.ast: Node = Node.to(ast)
        self.comment: Optional[Rule] = None
        self.rules: Dict[str, Rule] = collections.OrderedDict()
        self.pragmas: List[Rule] = []
        self.starting_rule: Optional[str] = None
        self.tokens: Set[str] = set()
        self.whitespace: Optional[Rule] = None
        self.assoc: Dict[str, str] = {}
        self.prec: Dict[str, int] = {}
        self.exception_needed: bool = False
        self.leftrec_needed: bool = False
        self.lookup_needed: bool = False
        self.operator_needed: bool = False
        self.unicat_needed: bool = False
        self.ch_needed: bool = False
        self.str_needed: bool = False
        self.range_needed: bool = False
        self.re_needed: bool = False
        self.needed_builtin_functions: List[str] = []
        self.needed_builtin_rules: List[str] = []
        self.needed_operators: List[str] = [
            'error',
            'fail',
            'offsets',
            'rewind',
            'succeed',
        ]
        self.unicodedata_needed: bool = False
        self.seeds_needed: bool = False

        self.operators: Dict[str, OperatorState] = {}
        self.leftrec_rules: Set[str] = set()
        self.outer_scope_rules: Set[str] = set()
        self.externs: Dict[str, bool] = {}

        has_starting_rule = False
        for rule in self.ast.rules:
            if rule.name.startswith('%'):
                self.pragmas.append(rule)
            elif not has_starting_rule:
                self.starting_rule = rule.name
                has_starting_rule = True
            self.rules[rule.name] = rule.child

    def node(self, cls, *args, **kwargs) -> Node:
        n = cls(*args, **kwargs)
        return self.update_node(n)

    def update_node(self, node: Node) -> Node:
        self._set_can_fail(node)
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
        for rule in self.ast.rules:
            self.rules[rule.name] = rule.child
            rules.add(rule.name)
        for rule_name in self.rules:
            if rule_name not in rules:
                self.ast.rules.append(Rule(rule_name, self.rules[rule_name]))

    # TODO: Figure out what to do with `inline`; it seems like there are
    # might be places where it's safe to ignore if something can fail if
    # inlined but not otherwise. See the commented-out lines below.
    def _can_fail(self, node: Node, inline: bool = True) -> bool:
        if node.can_fail_set():
            return node.can_fail
        if node.t in ('action', 'empty', 'opt', 'star'):
            return False
        if node.t == 'apply':
            assert isinstance(node, Apply)
            if node.rule_name in ('any', 'r_any', 'end', 'r_end'):
                return True
            # return self._can_fail(self.rules[node.rule_name], inline=False)
            return self._can_fail(self.rules[node.rule_name], inline)
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
            assert isinstance(node, Count)
            return node.start != 0
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


class Node:
    v_alias: Optional[str] = None
    v_aliases: List[str] = []
    ch_alias: Optional[str] = None
    ch_aliases: List[str] = []
    derived_attrs: List[str] = []

    @classmethod
    def to(cls, val: List[Any]) -> 'Node':
        assert len(val) == 3
        assert isinstance(val[0], str)
        assert isinstance(val[2], list)
        match val[0]:
            case 'action':
                return Action(Node.to(val[2][0]))
            case 'apply':
                return Apply(val[1])
            case 'choice':
                return Choice([Node.to(sn) for sn in val[2]])
            case 'count':
                return Count(Node.to(val[2][0]), val[1][0], val[1][1])
            case 'empty':
                return Empty()
            case 'ends_in':
                return EndsIn(Node.to(val[2][0]))
            case 'equals':
                return Equals(Node.to(val[2][0]))
            case 'e_arr':
                return EArr([Node.to(sn) for sn in val[2]])
            case 'e_call':
                return ECall([Node.to(sn) for sn in val[2]])
            case 'e_const':
                return EConst(val[1])
            case 'e_getitem':
                return EGetitem(Node.to(val[2][0]))
            case 'e_lit':
                return ELit(val[1])
            case 'e_num':
                return ENum(val[1])
            case 'e_var':
                return Var(val[1])
            case 'e_not':
                return ENot(Node.to(val[2][0]))
            case 'e_minus':
                return EMinus(Node.to(val[2][0]), Node.to(val[2][1]))
            case 'e_paren':
                return EParen(Node.to(val[2][0]))
            case 'e_plus':
                return EPlus(Node.to(val[2][0]), Node.to(val[2][1]))
            case 'e_qual':
                return EQual([Node.to(sn) for sn in val[2]])
            case 'label':
                return Label(val[1], Node.to(val[2][0]))
            case 'leftrec':
                return Leftrec(val[1], Node.to(val[2][0]))
            case 'lit':
                return Lit(val[1])
            case 'not':
                return Not(Node.to(val[2][0]))
            case 'not_one':
                return NotOne(Node.to(val[2][0]))
            case 'op':
                return Op(val[1][0], val[1][1], Node.to(val[2][0]))
            case 'operator':
                return Operator(val[1], [Node.to(sn) for sn in val[2]])
            case 'opt':
                return Opt(Node.to(val[2][0]))
            case 'paren':
                return Paren(Node.to(val[2][0]))
            case 'plus':
                return Plus(Node.to(val[2][0]))
            case 'pred':
                return Pred(Node.to(val[2][0]))
            case 'range':
                return Range(val[1][0], val[1][1])
            case 'regexp':
                return Regexp(val[1])
            case 'rule':
                return Rule(val[1], Node.to(val[2][0]))
            case 'rules':
                return Rules([Node.to(sn) for sn in val[2]])
            case 'run':
                return Run(Node.to(val[2][0]))
            case 'scope':
                return Scope([Node.to(sn) for sn in val[2]])
            case 'set':
                return Set(val[1])
            case 'seq':
                return Seq([Node.to(sn) for sn in val[2]])
            case 'plus':
                return Plus(Node.to(val[2][0]))
            case 'star':
                return Star(Node.to(val[2][0]))
            case 'unicat':
                return Unicat(val[1])
            case _:
                raise ValueError(f'Unexpected AST node type "{val[0]}"')

    def __init__(self, t: str, v: Any, ch: List['Node']):
        self.t: str = t
        self.v: Any = v
        self.ch: List['Node'] = ch
        self._can_fail: Optional[bool] = None

    def __getattr__(self, attr: str) -> Any:
        if attr == 'child':
            assert len(self.ch) == 1
            return self.ch[0]

        if attr == self.v_alias:
            attr = 'v'
        if attr == self.ch_alias:
            attr = 'ch'
            return self.ch
        if attr in self.v_aliases:
            return self.v[self.v_aliases.index(attr)]
        if attr in self.ch_aliases:
            return self.ch[self.ch_aliases.index(attr)]
        return super().__getattribute__(attr)

    def __setattr__(self, attr: str, v: Any) -> None:
        if attr == 'child':
            assert len(self.ch) == 1
            self.ch[0] = v
            return
        if attr == self.v_alias:
            attr = 'v'
        elif attr == self.ch_alias:
            attr = 'ch'
        super().__setattr__(attr, v)

    def __getitem__(self, i: int) -> Union[str | Any | List['Node']]:
        assert 0 <= i <= 2
        if i == 0:
            return self.t
        if i == 1:
            return self.v
        return self.ch

    def __setitem__(self, i: int, v: Any) -> None:
        assert 0 <= i <= 2
        if i == 0:
            self.t = v
        elif i == 1:
            self.v = v
        else:
            self.ch = v

    def __eq__(self, other) -> bool:
        assert isinstance(other, Node)
        return (
            self.t == other.t
            and self.v == other.v
            and self.ch == other.ch
            and self._can_fail == other._can_fail
        )

    def __repr__(self):
        s = self.__class__.__name__ + '('
        s += ', '.join(f'{a}={repr(getattr(self, a))}' for a in self.attrs)
        s += ')'
        return s

    def __len__(self):
        return 3

    @property
    def can_fail(self):
        assert self._can_fail is not None
        return self._can_fail

    @can_fail.setter
    def can_fail(self, flag: bool):
        self._can_fail = flag

    def can_fail_set(self) -> bool:
        return self._can_fail is not None

    @property
    def attrs(self) -> Tuple[str, ...]:
        fn = self.__class__.__init__.__code__
        return fn.co_varnames[1 : fn.co_argcount]

    def to_json(self, include_derived=False) -> Any:
        d: Dict[str, Any] = {}
        d['t'] = self.t
        attrs = list(self.attrs)
        child = 'child' in attrs
        if child:
            attrs.remove('child')
        ch = 'ch' in self.attrs
        if ch:
            attrs.remove('ch')
        if self.ch_alias:
            attrs.remove(self.ch_alias)
        for a in attrs:
            v = getattr(self, a)
            if isinstance(v, list):
                d[a] = [c.to_json(include_derived) for c in v]
            elif isinstance(v, Node):
                d[a] = v.to_json(include_derived)
            else:
                d[a] = v
        if include_derived:
            d['can_fail'] = self.can_fail
            for a in self.derived_attrs:
                d[a] = getattr(self, a)
        if child:
            d['child'] = self.child.to_json(include_derived)
        if self.ch_alias:
            d[self.ch_alias] = [c.to_json(include_derived) for c in self.ch]
        if ch:
            d['ch'] = [c.to_json(include_derived) for c in self.ch]
        return d


class Action(Node):
    def __init__(self, child):
        super().__init__('action', None, [child])


class Apply(Node):
    v_alias = 'rule_name'
    derived_attrs = ['memoize']

    def __init__(self, rule_name):
        super().__init__('apply', rule_name, [])
        # This will only be set by the generator.
        self.memoize = None


class Choice(Node):
    def __init__(self, ch):
        super().__init__('choice', None, ch)


class Count(Node):
    v_aliases = ['start', 'stop']

    def __init__(self, child, start, stop):
        super().__init__('count', [start, stop], [child])


class EArr(Node):
    def __init__(self, ch):
        super().__init__('e_arr', None, ch)


class ECall(Node):
    def __init__(self, ch):
        super().__init__('e_call', None, ch)


class EConst(Node):
    def __init__(self, v):
        super().__init__('e_const', v, [])


class EGetitem(Node):
    def __init__(self, child):
        super().__init__('e_getitem', None, [child])


class ELit(Node):
    def __init__(self, v):
        super().__init__('e_lit', v, [])


class EParen(Node):
    def __init__(self, child):
        super().__init__('e_paren', None, [child])


class EMinus(Node):
    ch_aliases = ['left', 'right']

    def __init__(self, left, right):
        super().__init__('e_minus', None, [left, right])


class ENot(Node):
    def __init__(self, ch):
        super().__init__('e_not', None, [ch])


class ENum(Node):
    def __init__(self, v):
        super().__init__('e_num', v, [])


class EPlus(Node):
    ch_aliases = ['left', 'right']

    def __init__(self, left, right):
        super().__init__('e_plus', None, [left, right])


class EQual(Node):
    def __init__(self, ch):
        super().__init__('e_qual', None, ch)


class Empty(Node):
    def __init__(self):
        super().__init__('empty', None, [])


class EndsIn(Node):
    def __init__(self, child):
        super().__init__('ends_in', None, [child])


class Equals(Node):
    def __init__(self, child):
        super().__init__('equals', None, [child])


class Label(Node):
    v_alias = 'name'
    derived_attrs = ['outer_scope']

    def __init__(self, name, child):
        super().__init__('label', name, [child])
        self.outer_scope = False


class Leftrec(Node):
    v_alias = 'name'
    derived_attrs = ['leftrec']

    def __init__(self, name, child):
        super().__init__('leftrec', name, [child])
        self.left_assoc = None


class Lit(Node):
    def __init__(self, v):
        super().__init__('lit', v, [])


class Not(Node):
    def __init__(self, child):
        super().__init__('not', None, [child])


class NotOne(Node):
    def __init__(self, child):
        super().__init__('not_one', None, [child])


class Op(Node):
    v_aliases = ['op', 'prec']

    def __init__(self, op, prec, child):
        super().__init__('op', [op, prec], [child])


class Operator(Node):
    v_alias = 'name'

    def __init__(self, name, ch):
        super().__init__('operator', name, ch)


class Opt(Node):
    def __init__(self, child):
        super().__init__('opt', None, [child])


class Paren(Node):
    def __init__(self, child):
        super().__init__('choice', None, [child])


class Plus(Node):
    def __init__(self, child):
        super().__init__('plus', None, [child])


class Pred(Node):
    def __init__(self, child):
        super().__init__('pred', None, [child])


class Range(Node):
    v_aliases = ['start', 'stop']

    def __init__(self, start, stop):
        super().__init__('range', [start, stop], [])


class Regexp(Node):
    def __init__(self, v):
        super().__init__('regexp', v, [])


class Rule(Node):
    v_alias = 'name'
    derived_attrs = ['local_vars']

    def __init__(self, name, child):
        super().__init__('rule', name, [child])
        # Note: This will not actually be derived until the generator
        # does so.
        self.local_vars = []


class Rules(Node):
    ch_alias = 'rules'

    def __init__(self, rules):
        super().__init__('rules', None, rules)


class Run(Node):
    def __init__(self, child):
        super().__init__('run', None, [child])


class Scope(Node):
    def __init__(self, ch):
        super().__init__('scope', None, ch)


class Seq(Node):
    derived_attrs = ['vars']

    def __init__(self, ch):
        super().__init__('seq', None, ch)
        self.vars = []


class Set(Node):
    def __init__(self, v):
        super().__init__('set', v, [])


class Star(Node):
    def __init__(self, child):
        super().__init__('star', None, [child])


class Unicat(Node):
    def __init__(self, v):
        super().__init__('unicat', v, [])


class Val(Node):
    def __init__(self, t, val):
        super().__init__(t, val, [])


class Var(Node):
    derived_attrs = ['outer_scope']

    def __init__(self, name):
        super().__init__('e_var', name, [])
        self.outer_scope = False

    @property
    def name(self):
        return self.v
