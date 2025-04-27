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
            case ('e_arr' | 'e_call' | 'e_const' | 'e_getitem' | 'e_lit' |
                 'e_minus' | 'e_num' | 'e_not' | 'e_paren' | 'e_plus' |
                 'e_qual' | 'e_var'):
                return Expr(val[0], val[1], [Node.to(sn) for sn in val[2]])
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
        self, ty: str, val: Any = None, children: Optional[List['Node']] = None
    ):
        self.t: str = ty
        self.v: Any = val
        self.ch: List['Node'] = children or []

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

    def __eq__(self, other):
        if isinstance(other, Node):
            return (
                self.t == other.t and
                self.v == other.v and
                self.ch == other.ch
            )
        return (
            self.t == other[0] and
            self.v == other[1] and
            self.ch == other[2]
        )

    def __repr__(self):
        return f'Node({repr(self.t)}, {repr(self.v)}, {repr(self.ch)})'

    def __len__(self):
        return 3

    @property
    def child(self):
        return self.ch[0]


class Action(Node):
    def __init__(self, child):
        super().__init__('action', None, [child])

    def __repr__(self):
        return f'Action(ch={repr(self.ch)})'


class Apply(Node):
    def __init__(self, rule):
        super().__init__('apply', rule, [])

    def __repr__(self):
        return f'Apply({repr(self.rule)})'

    @property
    def rule(self):
        return self.v


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


class Expr(Node):
    def __init__(self, ty, val, ch):
        super().__init__(ty, val, ch)

    def __repr__(self):
        return f'Expr({repr(self.t)}, {repr(self.v)}, {repr(self.ch)})'


class Label(Node):
    def __init__(self, name, child):
        super().__init__('label', name, [child])

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
        return f'Regexp({repr(self.val)})'


class Rule(Node):
    def __init__(self, name, child):
        super().__init__('rule', name, [child])

    @property
    def name(self):
        return self.v

    def __repr__(self):
        return f'Rule(name={repr(self.name)}, {repr(self.child)})'


class Rules(Node):
    def __init__(self, ch):
        super().__init__('rules', None, ch)

    def __repr__(self):
        return f'Rules({repr(self.ch)})'


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
        return f'(Seq(ch={repr(self.ch)})'


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


class Unicat(Node):
    def __init__(self, v):
        super().__init__('unicat', v, [])

    def __repr__(self):
        return f'Unicat({repr(self.v)})'




class AnalysisError(Exception):
    """Raised when something fails one or more static analysis checks."""

    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        s = 'Errors were found:\n  '
        s += '\n  '.join(error for error in self.errors)
        s += '\n'
        return s


class Grammar:
    def __init__(self, ast):
        self.ast = Node.to(ast)
        self.comment = None
        self.rules = collections.OrderedDict()
        self.pragmas = []
        self.starting_rule = None
        self.tokens = set()
        self.whitespace = None
        self.assoc = {}
        self.prec = {}
        self.exception_needed = False
        self.leftrec_needed = False
        self.operator_needed = False
        self.unicat_needed = False
        self.ch_needed = False
        self.str_needed = False
        self.range_needed = False
        self.re_needed = False
        self.needed_builtin_functions = set()
        self.needed_builtin_rules = set()
        self.operators = {}
        self.leftrec_rules = set()
        self.outer_scope_rules = set()
        self.externs = {}

        has_starting_rule = False
        for n in self.ast[2]:
            if n[1].startswith('%'):
                self.pragmas.append(n)
            elif not has_starting_rule:
                self.starting_rule = n[1]
                has_starting_rule = True
            self.rules[n[1]] = n[2][0]

    def update_rules(self):
        # Update grammar.rules to match grammar.ast for rules in
        # grammar.ast and then append any new rules to grammar.ast.
        rules = set()
        for rule in self.ast[2]:
            self.rules[rule[1]] = rule[2][0]
            rules.add(rule[1])
        for rule in self.rules:
            if rule not in rules:
                self.ast[2].append(Rule(rule, self.rules[rule]))


class OperatorState:
    def __init__(self):
        self.prec_ops = {}
        self.rassoc = set()
        self.choices = {}


def analyze(ast, rewrite_subrules: bool) -> Grammar:
    """Analyze and optimize the AST.

    This runs any static analysis we can do over the grammars and
    optimizes what we can. Raises AnalysisError if there are any errors.
    """

    g = Grammar(ast)

    # Find whatever errors we can.
    a = _Analyzer(g)
    a.add_pragmas()

    # Add in the _whitespace, _comment, and _filler rules.
    _add_filler_rules(g)

    a.run_checks()
    if a.errors:
        raise AnalysisError(a.errors)

    # Rewrite the AST to insert scopes as needed.
    _rewrite_scopes(g)

    # Rewrite the AST to insert leftrec and operator nodes as needed.
    _rewrite_recursion(g)

    # Insert filler nodes.
    _rewrite_filler(g)

    _rewrite_pragma_rules(g)

    # Rewrite any choice or seq nodes that only have one child.
    _rewrite_singles(g)

    # Extract subnodes into their own rules to make codegen easier.
    if rewrite_subrules:
        # Extract subnodes into their own rules to make codegen easier.
        # Not needed when just interpreting the grammar.
        _rewrite_subrules(g)

    # TODO: Figure out how to statically analyze predicates to
    # catch ones that don't return booleans, so that we don't need
    # to worry about runtime exceptions where possible.
    def _exception_needed(node):
        if node[0] == 'pred':
            return True
        return any(_exception_needed(sn) for sn in node[2])

    g.exception_needed = _exception_needed(g.ast)

    return g


BUILTIN_FUNCTIONS = (
    'atof',
    'atoi',
    'atou',
    'cat',
    'concat',
    'cons',
    'dedent',
    'dict',
    'float',
    'int',
    'itou',
    'join',
    'otou',
    'scat',
    'scons',
    'strcat',
    'unicode_lookup',
    'utoi',
    'xtou',
)


BUILTIN_RULES = (
    'any',
    'end',
)


class _Analyzer:
    def __init__(self, grammar):
        self.grammar = grammar
        assert self.grammar.ast[0] == 'rules'
        self.errors = []
        self.current_prec = 0
        self.current_rule = None

    def add_pragmas(self):
        for node in self.grammar.ast[2]:
            self.current_rule = node[1]
            if node[1][0] == '%':
                self.check_pragma(node)
                continue

    def run_checks(self):
        for node in self.grammar.ast[2]:
            if node[1].startswith('_'):
                self.errors.append(
                    f'Illegal rule name "{node[1]}": '
                    'names starting with an "_" are reserved'
                )
            self.current_rule = node[1]
            if node[1][0] == '%':
                continue
            self.check_for_unknown_rules(node)
            self.check_for_unknown_functions(node)
            self.check_positional_vars(node)
            self.check_named_vars(node)

    def check_pragma(self, node):
        pragma = node[1]
        choice = node[2][0]

        if pragma == '%externs':
            self._collect_externs(node)
        elif pragma == '%tokens':
            self._collect_idents(self.grammar.tokens, node)
            for t in self.grammar.tokens:
                if t not in self.grammar.rules:
                    self.errors.append(f'Unknown token rule "{t}"')
        elif pragma == '%whitespace':
            self.grammar.whitespace = choice
        elif pragma == '%comment':
            self.grammar.comment = choice
        elif pragma == '%prec':
            operators = set()
            for c in choice[2]:
                self._collect_operators(operators, c)
                for op in operators:
                    self.grammar.prec[op] = self.current_prec
                self.current_prec += 2
        elif pragma == '%assoc':
            choice = node[2][0]
            seq = choice[2][0]
            operator = seq[2][0][1]
            direction = seq[2][1][1]
            self.grammar.assoc[operator] = direction
        else:
            self.errors.append(f'Unknown pragma "{pragma}"')

    def _collect_externs(self, n):
        assert n[2][0][0] == 'choice'
        for choice in n[2][0][2]:
            assert choice[0] == 'seq'
            assert choice[2][0][0] == 'apply'
            key = choice[2][0][1]
            assert choice[2][1][0] == 'action'
            assert choice[2][1][2][0][0] == 'e_const'
            assert choice[2][1][2][0][1] in ('true', 'false')
            value = True if choice[2][1][2][0][1] == 'true' else False
            self.grammar.externs[key] = value

    def _collect_idents(self, s, n):
        if n[0] == 'apply':
            s.add(n[1])
        for sn in n[2]:
            self._collect_idents(s, sn)

    def _collect_operators(self, operators, node):
        if node[0] == 'lit':
            operators.add(node[1])
            return
        if node[0] == 'apply':
            if node[1] not in self.grammar.rules:
                self.errors.append(f'Unknown rule "{node[1]}"')
                return
            self._collect_operators(operators, self.grammar.rules[node[1]])
            return
        if node[0] in ('rule', 'choice', 'seq'):
            for sn in node[2]:
                self._collect_operators(operators, sn)
            return
        self.errors.append(f'Unexpected AST node type {node[0]} in %prec')

    def check_for_unknown_rules(self, node):
        if (
            node[0] == 'apply'
            and node[1] not in self.grammar.rules
            and node[1] not in ('any', 'end')
        ):
            self.errors.append(f'Unknown rule "{node[1]}"')
        for sn in node[2]:
            self.check_for_unknown_rules(sn)

    def check_positional_vars(self, node):
        """Checks that:
        - No one tries to define a positional var explicitly
          (e.g., `grammar = 'foo':$1` is bad).
        - Any reference to a positional var only happens after it would
          be defined  (e.g., `grammar = {$2}` is bad).
        And then rewrites the AST to insert label nodes for the needed
        positional vars.
        """
        if node[0] != 'seq':
            for n in node[2]:
                self.check_positional_vars(n)

        labels_needed = set()
        for i, n in enumerate(node[2], start=1):
            name = f'${i}'
            if n[0] == 'label':
                if n[1][0] == '$':
                    self.errors.append(
                        f'"{n[1]}" is a reserved variable name '
                        'and cannot be explicitly defined'
                    )
                self.check_positional_vars(n[2][0])
            if n[0] in ('action', 'equals', 'pred'):
                self._check_positional_var_refs(n[2][0], i, labels_needed)

        # Now define all the positional vars we need.
        for i, n in enumerate(node[2], start=1):
            name = f'${i}'
            if name in labels_needed:
                node[2][i - 1] = ['label', name, [n]]

    def _check_positional_var_refs(self, node, current_index, labels_needed):
        if node[0] == 'e_var':
            if node[1][0] == '$':
                num = int(node[1][1:])
                if num >= current_index:
                    self.errors.append(
                        f'Variable "{node[1]}" referenced before '
                        'it was available'
                    )
                else:
                    # We don't want to think of unknown variables as
                    # referenced, so just keep track of the known ones.
                    labels_needed.add(node[1])

        if node[0] == 'e_qual' and node[2][1][0] == 'e_call':
            assert node[2][0][0] == 'e_var'
            # Skip over the first child as it is a function name.
            start = 1
        else:
            start = 0
        for n in node[2][start:]:
            self._check_positional_var_refs(n, current_index, labels_needed)

    def check_for_unknown_functions(self, node):
        if node[0] == 'e_qual' and node[2][1][0] == 'e_call':
            name = node[2][0][1]
            if name not in BUILTIN_FUNCTIONS:
                self.errors.append(f'Unknown function "{name}" called')
        for n in node[2]:
            self.check_for_unknown_functions(n)

    def check_named_vars(self, node):
        assert node[0] == 'rule'
        labels = set()
        references = set()
        self._check_named_vars(node, labels, references)

    def _check_named_vars(self, node, labels, references):
        if node[0] == 'seq':
            outer_labels = labels.copy()
            local_labels = set()
            for n in node[2]:
                if n[0] == 'label':
                    if n[1][0] != '$':
                        labels.add(n[1])
                        local_labels.add(n[1])
                    self._check_named_vars(n[2][0], labels, references)
                else:
                    self._check_named_vars(n, labels, references)

            for v in local_labels - references:
                self.errors.append(f'Variable "{v}" never used')

            # Something referenced a variable in an outer scope.
            if references - local_labels:
                self.grammar.outer_scope_rules.add(self.current_rule)

            # Now remove any variables that were defined in this scope.
            for v in labels.difference(outer_labels):
                labels.remove(v)
            return

        if node[0] == 'e_var':
            if node[1] in labels:
                references.add(node[1])
            elif node[1] in self.grammar.externs:
                pass
            elif not node[1][0] == '$':
                self.errors.append(f'Unknown variable "{node[1]}" referenced')

        if node[0] == 'e_qual' and node[2][1][0] == 'e_call':
            # Skip over names that are functions.
            start = 1
        else:
            start = 0
        for n in node[2][start:]:
            self._check_named_vars(n, labels, references)


def _rewrite_scopes(grammar):
    def rewrite_node(node):
        for i in range(len(node[2])):
            node[2][i] = rewrite_node(node[2][i])
        if node[0] == 'seq' and any(sn[0] == 'label' for sn in node[2]):
            return Scope([node])
        return node

    for rule in grammar.ast[2]:
        if rule[1] in grammar.outer_scope_rules:
            rule[2][0] = rewrite_node(rule[2][0])


def _rewrite_recursion(grammar):
    """Rewrite the AST to insert leftrec and operator nodes as needed."""
    for node in grammar.ast[2]:
        if node[1][0] == '%':
            continue
        name = node[1]
        assert node[2][0][0] == 'choice'
        choices = node[2][0][2]

        operator_node = _check_operator(grammar, name, choices)
        if operator_node:
            name = operator_node[2][0][1]
            node[2] = [operator_node]
            grammar.rules[name] = operator_node
            continue

        for i, choice in enumerate(choices):
            seen = set()
            has_lr = _check_lr(name, choice, grammar, seen)
            if has_lr:
                grammar.leftrec_rules.update(seen)
                choices[i] = Leftrec('%s#%d' % (name, i + 1), choice)


def _check_operator(grammar, name, choices):
    if len(choices) == 1:
        return None
    operators = []
    for choice in choices[:-1]:
        has_scope = choice[0] == 'scope'
        if has_scope:
            # TODO: is this the right logic?
            choice = choice[2][0]
        assert choice[0] == 'seq'
        if len(choice[2]) not in (3, 4):
            return None
        if (choice[2][0] != Label('$1', Apply(name)) and
            choice[2][0] != Apply(name)):
            return None
        if choice[2][1][0] != 'lit' or choice[2][1][1] not in grammar.prec:
            return None
        operator = choice[2][1][1]
        prec = grammar.prec[operator]
        if (choice[2][2] != Label('$3', Apply(name)) and
            choice[2][2] != Apply(name)):
            return None
        if len(choice[2]) == 4 and choice[2][3][0] != 'action':
            return None
        if has_scope:
            choice = Scope([choice])
        operators.append(['op', [operator, prec], [choice]])
    choice = choices[-1]
    if len(choice[2]) != 1:
        return None
    return Choice([Operator(name, operators), choices[-1]])


def _check_lr(name, node, grammar, seen):
    # pylint: disable=too-many-branches
    ty = node[0]
    if ty == 'apply':
        if node[1] == name:
            seen.add(name)
            return True  # Direct recursion.
        if node[1] in ('any', 'anything', 'end'):
            return False
        if node[1] in seen:
            # We've hit left recursion on a different rule, so, no.
            return False
        seen.add(node[1])
        return _check_lr(name, grammar.rules[node[1]], grammar, seen)
    if ty in ('lit', 'ends_in', 'not_one', 'plus', 'unicat'):
        return False
    if ty == 'seq':
        for subnode in node[2]:
            if subnode[0] == 'lit':
                return False
            r = _check_lr(name, subnode, grammar, seen)
            if r is not None:
                return r
        return False
    if ty == 'choice':
        for n in node[2]:
            r = _check_lr(name, n, grammar, seen)
            if r is not None:
                return r
        return None
    if ty in ('opt', 'star'):
        return None
    if ty in (
        'count',
        'label',
        'not',
        'opt',
        'paren',
        'run',
        'scope',
        'star',
    ):
        return _check_lr(name, node[2][0], grammar, seen)

    # If we get here, either this is an unknown AST node type, or
    # it is one we think we shouldn't be able to reach, like an
    # operator node or a e_* node.
    assert ty in (
        'action',
        'empty',
        'equals',
        'leftrec',
        'pred',
        'range',
        'regexp',
        'set',
    ), (
        'unexpected AST node type %s' % ty  # pragma: no cover
    )
    return False


def _rewrite_filler(grammar):
    """Rewrites the grammar to insert filler rules and nodes."""
    if not grammar.comment and not grammar.whitespace:
        return

    # Compute the transitive closure of all the token rules.
    _collect_tokens(grammar, grammar.ast)

    # Now rewrite all the rules to insert the filler nodes.
    grammar.ast = _add_filler_nodes(grammar, grammar.ast)
    grammar.update_rules()


def _collect_tokens(grammar, node):
    # Collect the list of all rules reachable from this token rule:
    # all of them should be treated as tokens as well.
    if node[0] == 'rules':
        for sn in node[2]:
            if sn[1] in grammar.tokens:
                _collect_tokens(grammar, sn)
        return

    if node[0] == 'apply' and node[1] not in BUILTIN_RULES:
        grammar.tokens.add(node[1])

    for n in node[2]:
        _collect_tokens(grammar, n)


def _add_filler_rules(grammar):
    if grammar.whitespace:
        grammar.tokens.add('%whitespace')
    if grammar.comment:
        grammar.tokens.add('%comment')
    filler = None
    if grammar.whitespace and grammar.comment:
        if (
            grammar.whitespace[0] == 'regexp'
            and grammar.comment[0] == 'regexp'
        ):
            filler = Regexp(
                f'(({grammar.whitespace[1]})|({grammar.comment[1]}))*',
            )
        else:
            filler = Star(Choice([Apply('%whitespace'), Apply('%comment')]))
    elif grammar.comment:
        if grammar.comment[0] == 'regexp':
            filler = Regexp(f'({grammar.comment[1]})*')
        else:
            filler = Star(Apply('%comment'))
    elif grammar.whitespace:
        if grammar.whitespace[0] == 'regexp':
            filler = Regexp(f'({grammar.whitespace[1]})*')
        else:
            filler = Star(Apply('%whitespace'))
    if filler:
        grammar.rules['%filler'] = Choice([filler])


def _add_filler_nodes(grammar, node):
    def should_fill(node):
        if node[0] in ('escape', 'lit', 'range', 'regexp', 'set'):
            return True
        if node[0] == 'apply' and node[1] in (
            '%comment',
            '%filler',
            '%whitespace',
        ):
            return False
        if node[0] == 'apply' and (
            node[1] == 'end' or node[1] in grammar.tokens
        ):
            return True
        return False

    if node[0] == 'rule' and node[1].startswith('%'):
        # Don't mess with the pragmas.
        return node
    if node[0] == 'rule' and node[1] in grammar.tokens:
        # By definition we don't want to insert filler into token rules.
        return node
    if node[0] == 'rule' and node[1] in ('%comment', '%filler', '%whitespace'):
        # These *are* the filler rules, so we don't want to insert filler
        # into them.
        return node
    if node[0] == 'seq':
        children = []
        for child in node[2]:
            if should_fill(child):
                children.append(Apply('%filler'))
                children.append(child)
            else:
                sn = _add_filler_nodes(grammar, child)
                children.append(sn)
        return Seq(children)
    if should_fill(node):
        return Paren(Seq([Apply('%filler'), node]))

    r = Node.to([node[0], node[1], [_add_filler_nodes(grammar, n) for n in node[2]]])
    return r


def _rewrite_singles(grammar):
    """Replace any choice or seq nodes in the AST with only one child as
    that child."""

    def walk(node):
        if node[0] in ('choice', 'seq') and len(node[2]) == 1:
            return walk(node[2][0])
        return Node.to([node[0], node[1], [walk(n) for n in node[2]]])

    grammar.ast = walk(grammar.ast)
    grammar.update_rules()


def _rewrite_subrules(grammar):
    """Extracts subrules from rules as needed to be able to generate
    code properly."""
    sr = _SubRuleRewriter(grammar, 'r_{rule}', 's_{rule}_{counter}')
    sr.rewrite()


class _SubRuleRewriter:
    def __init__(self, grammar, rule_fmt, subrule_fmt):
        self._grammar = grammar
        self._rule_fmt = rule_fmt
        self._subrule_fmt = subrule_fmt
        self._rule = None
        self._counter = 0
        self._methods = {}
        self._subrules = {}

    def rewrite(self):
        for rule, node in self._grammar.rules.items():
            self._rule = rule
            self._subrules = {}
            self._counter = 0
            new_node = self._walk(node)
            self._methods[self._rule_fmt.format(rule=rule)] = new_node
            subrules = sorted(self._subrules.keys(), key=self._subrule_key)
            for subrule in subrules:
                self._methods[subrule] = self._subrules[subrule]
        self._grammar.rules = self._methods
        rules = []
        for rule in self._grammar.rules:
            rules.append(Rule(rule, self._grammar.rules[rule]))
        self._grammar.ast = Rules(rules)

    def _subrule(self) -> str:
        self._counter += 1
        return self._subrule_fmt.format(rule=self._rule, counter=self._counter)

    def _subrule_key(self, s: str) -> int:
        return int(
            s.replace('s_{rule}_'.format(rule=self._rule), '').replace('_', '')
        )

    def _walk(self, node):
        fn = getattr(self, f'_ty_{node[0]}', None)
        if fn:
            return fn(node)
        return self._walkn(node)

    def _walkn(self, node):
        subnodes = []
        for child in node[2]:
            if self._can_inline(child):
                subnodes.append(self._walk(child))
            else:
                subnodes.append(self._make_subrule(child))
        return Node.to([node[0], node[1], subnodes])

    def _split1(self, node):
        return Node.to([node[0], node[1], [self._make_subrule(node[2][0])]])

    def _can_inline(self, node) -> bool:
        return node[0] not in (
            'choice',
            'count',
            'not',
            'opt',
            'plus',
            'regexp',
            'run',
            'set',
            'seq',
            'star',
        )

    def _make_subrule(self, child):
        subnode_rule = self._subrule()
        self._subrules[subnode_rule] = self._walk(child)
        return Apply(subnode_rule)

    def _ty_apply(self, node):
        if node.rule in ('any', 'end'):
            self._grammar.needed_builtin_rules.add(node[1])
        return Apply(self._rule_fmt.format(rule=node.rule))

    def _ty_ends_in(self, node):
        self._grammar.needed_builtin_rules.add('any')
        return self._walkn(node)

    def _ty_equals(self, node):
        self._grammar.ch_needed = True
        self._grammar.str_needed = True
        return node

    def _ty_leftrec(self, node):
        self._grammar.leftrec_needed = True
        return self._split1(node)

    def _ty_lit(self, node):
        self._grammar.ch_needed = True
        if len(node[1]) > 1:
            self._grammar.str_needed = True
        return node

    def _ty_e_qual(self, node):
        if node[2][0][0] == 'e_var' and node[2][1][0] == 'e_call':
            self._grammar.needed_builtin_functions.add(node[2][0][1])
        return self._walkn(node)

    def _ty_not_one(self, node):
        self._grammar.needed_builtin_rules.add('any')
        return self._walkn(node)

    def _ty_operator(self, node):
        self._grammar.operator_needed = True
        o = OperatorState()
        for operator in node[2]:
            op, prec = operator[1]
            subnode = operator[2][0]
            o.prec_ops.setdefault(prec, []).append(op)
            if self._grammar.assoc.get(op) == 'right':
                o.rassoc.add(op)
            subnode_rule = self._subrule()
            o.choices[op] = subnode_rule
            self._subrules[subnode_rule] = self._walk(subnode)
        self._grammar.operators[node[1]] = o
        return Node.to([node[0], node[1], []])

    def _ty_paren(self, node):
        return self._split1(node)

    def _ty_range(self, node):
        self._grammar.range_needed = True
        return node

    def _ty_regexp(self, node):
        self._grammar.re_needed = True
        return node

    def _ty_set(self, node):
        self._grammar.re_needed = True
        return node

    def _ty_unicat(self, node):
        self._grammar.unicat_needed = True
        return node


def _rewrite_pragma_rules(grammar):
    # '%' is not a legal character to be in an identifier in most programming
    # languages, so we need to rewrite rule names containing '%' to something
    # else.
    def _rewrite(node):
        if node[0] == 'apply' and node[1].startswith('%'):
            return Apply(node[1].replace('%', '_'))
        return Node.to([node[0], node[1], [_rewrite(sn) for sn in node[2]]])

    new_rules = []
    for rule in grammar.ast[2]:
        if rule[1].startswith('%'):
            if rule[1] in ('%comment', '%whitespace', '%filler'):
                new_rule = Rule(
                    rule.name.replace('%', '_'), _rewrite(rule.child),
                )
                new_rules.append(new_rule)
                assert new_rule[1] not in grammar.rules, (
                    f'Collision with existing rule {new_rule[1]}'
                )
                grammar.rules[new_rule[1]] = new_rule[2][0]
            if rule[1] in grammar.rules:
                del grammar.rules[rule[1]]
        else:
            new_rules.append(_rewrite(rule))
    grammar.ast = Rules(new_rules)
