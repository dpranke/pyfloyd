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
from typing import Any, List, Optional, Union


class Node:
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
            case 'e_const':
                return Const(val[1])
            case 'e_lit' | 'e_num':
                return Val(val[0], val[1])
            case 'e_var':
                return Var(val[1])
            case 'e_getitem' | 'e_paren' | 'e_not':
                return UnaryExpr(val[0], Node.to(val[2][0]))
            case 'e_plus' | 'e_minus':
                return BinExpr(val[0], Node.to(val[2][0]), Node.to(val[2][1]))
            case 'e_arr' | 'e_call' | 'e_qual':
                return ListExpr(val[0], [Node.to(sn) for sn in val[2]])
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

    def __init__(
        self,
        ty: str,
        val: Any = None,
        children: Optional[List['Node']] = None,
    ):
        self.t: str = ty
        self.v: Any = val
        self.ch: List['Node'] = children or []
        self._can_fail: Optional[bool] = None

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
        return f'Node({repr(self.t)}, {repr(self.v)}, {repr(self.ch)})'

    def __len__(self):
        return 3

    @property
    def child(self):
        assert len(self.ch) == 1
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


class Action(Node):
    def __init__(self, child):
        super().__init__('action', None, [child])

    def __repr__(self):
        return f'Action(ch={repr(self.ch)})'


class Apply(Node):
    def __init__(self, rule_name):
        super().__init__('apply', rule_name, [])

    def __repr__(self):
        return f'Apply({repr(self.rule_name)})'

    @property
    def rule_name(self):
        return self.v

    @rule_name.setter
    def rule_name(self, v):
        self.v = v


class BinExpr(Node):
    def __init__(self, ty, left, right):
        super().__init__(ty, None, [left, right])

    def __repr__(self):
        return (
            f'BinExpr({repr(self.t)}, {repr(self.left)}, {repr(self.right)})'
        )

    @property
    def left(self):
        return self.ch[0]

    @property
    def right(self):
        return self.ch[1]


class Choice(Node):
    def __init__(self, ch):
        super().__init__('choice', None, ch)

    def __repr__(self):
        return f'Choice(ch={repr(self.ch)})'


class Count(Node):
    def __init__(self, child, start, stop):
        super().__init__('count', [start, stop], [child])

    @property
    def start(self):
        return self.v[0]

    @property
    def stop(self):
        return self.v[1]

    def __repr__(self):
        return (
            f'Count({repr(self.child)}, {repr(self.start)}, {repr(self.stop)})'
        )


class Empty(Node):
    def __init__(self):
        super().__init__('empty', None, [])

    def __repr__(self):
        return f'Empty()'


class EndsIn(Node):
    def __init__(self, child):
        super().__init__('ends_in', None, [child])

    def __repr__(self):
        return f'EndsIn({repr(self.child)})'


class Equals(Node):
    def __init__(self, child):
        super().__init__('equals', None, [child])

    def __repr__(self):
        return f'Equals(ch={repr(self.ch)})'


class Const(Node):
    def __init__(self, val):
        return super().__init__('e_const', val, [])

    def __repr__(self):
        return f'Const({repr(self.v)})'


class ListExpr(Node):
    def __init__(self, ty, ch):
        super().__init__(ty, None, ch)

    def __repr__(self):
        return f'ListExpr({repr(self.t)}, {repr(self.ch)})'


class Label(Node):
    def __init__(self, name, child):
        super().__init__('label', name, [child])
        self.outer_scope = False

    @property
    def name(self):
        return self.v

    def __repr__(self):
        return f'Label(name={repr(self.name)}, child={repr(self.child)})'


class Leftrec(Node):
    def __init__(self, name, child):
        super().__init__('leftrec', name, [child])

    @property
    def name(self):
        return self.v

    def __repr__(self):
        return f'Leftrec(name={repr(self.name)}, child={repr.self.child})'


class Lit(Node):
    def __init__(self, val):
        super().__init__('lit', val, [])

    def __repr__(self):
        return f'Lit({repr(self.v)})'


class Not(Node):
    def __init__(self, child):
        super().__init__('not', None, [child])

    def __repr__(self):
        return f'Not({repr(self.child)})'


class NotOne(Node):
    def __init__(self, child):
        super().__init__('not_one', None, [child])

    def __repr__(self):
        return f'NotOne({repr(self.child)})'


class Op(Node):
    def __init__(self, op, prec, child):
        super().__init__('op', [op, prec], [child])

    def __repr__(self):
        return f'Op(op={self.op}, prec={self.prec}, child={self.child})'

    @property
    def op(self):
        return self.v[0]

    @property
    def prec(self):
        return self.v[1]


class Operator(Node):
    def __init__(self, name, ch):
        super().__init__('operator', name, ch)

    @property
    def name(self):
        return self.v

    def __repr__(self):
        return f'Operator(name={repr(self.name)}, ch={repr(self.ch)})'


class Opt(Node):
    def __init__(self, child):
        super().__init__('opt', None, [child])

    def __repr__(self):
        return f'Opt({repr(self.child)})'


class Paren(Node):
    def __init__(self, child):
        super().__init__('choice', None, [child])

    def __repr__(self):
        return f'(Paren({repr(self.child)})'


class Plus(Node):
    def __init__(self, child):
        super().__init__('plus', None, [child])

    def __repr__(self):
        return f'Plus({repr(self.child)})'


class Pred(Node):
    def __init__(self, child):
        super().__init__('pred', None, [child])

    def __repr__(self):
        return f'Pred({repr(self.child)})'


class Range(Node):
    def __init__(self, start, stop):
        super().__init__('range', [start, stop], [])

    @property
    def start(self):
        return self.v[0]

    @property
    def stop(self):
        return self.v[1]

    def __repr__(self):
        return f'Range({repr(self.start)}, {repr(self.stop)})'


class Regexp(Node):
    def __init__(self, val):
        super().__init__('regexp', val, [])

    def __repr__(self):
        return f'Regexp({repr(self.v)})'


class Rule(Node):
    def __init__(self, name, child):
        super().__init__('rule', name, [child])

    @property
    def name(self):
        return self.v

    @name.setter
    def name(self, v):
        self.v = v

    def __repr__(self):
        return f'Rule(name={repr(self.name)}, {repr(self.child)})'


class Rules(Node):
    def __init__(self, ch):
        super().__init__('rules', None, ch)

    def __repr__(self):
        return f'Rules({repr(self.ch)})'

    @property
    def rules(self):
        return self.ch

    @rules.setter
    def rules(self, ch):
        self.ch = ch


class Run(Node):
    def __init__(self, child):
        super().__init__('run', None, [child])

    def __repr__(self):
        return f'Run({repr(self.child)})'


class Scope(Node):
    def __init__(self, ch):
        super().__init__('scope', None, ch)

    def __repr__(self):
        return f'(Scope(ch={repr(self.ch)})'


class Seq(Node):
    def __init__(self, ch):
        super().__init__('seq', None, ch)

    def __repr__(self):
        return f'Seq(ch={repr(self.ch)})'


class Set(Node):
    def __init__(self, val):
        super().__init__('set', val, [])

    def __repr__(self):
        return f'Set({repr(self.v)})'


class Star(Node):
    def __init__(self, child):
        super().__init__('star', None, [child])

    def __repr__(self):
        return f'Star({repr(self.child)})'


class UnaryExpr(Node):
    def __init__(self, ty, child):
        super().__init__(ty, None, [child])

    def __repr__(self):
        return f'UnaryExpr({repr(self.t)}, {repr(self.child)})'


class Unicat(Node):
    def __init__(self, v):
        super().__init__('unicat', v, [])

    def __repr__(self):
        return f'Unicat({repr(self.v)})'


class Val(Node):
    def __init__(self, ty, val):
        super().__init__(ty, val, [])

    def __repr(self):
        return f'Val({repr(self.t)}, {repr(self.v)})'


class Var(Node):
    def __init__(self, val):
        super().__init__('e_var', val, [])
        self.outer_scope = False

    def __repr__(self):
        return f'Var({repr(self.v)})'

    @property
    def name(self):
        return self.v
