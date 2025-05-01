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

from typing import Any, Dict, List, Optional, Tuple, Union


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

    def __init__(self, rule_name):
        super().__init__('apply', rule_name, [])


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

    def __init__(self, name, child):
        super().__init__('leftrec', name, [child])


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

    def __init__(self, name, child):
        super().__init__('rule', name, [child])


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
    derived_attrs = ['locals']

    def __init__(self, ch):
        super().__init__('seq', None, ch)
        self.locals = []


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
