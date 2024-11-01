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


class AnalysisError(Exception):
    """Raised when something fails one or more static analysis checks."""

    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        s = 'Errors were found:\n  '
        s += '\n  '.join(error for error in self.errors)
        s += '\n'
        return s


def _update_rules(grammar):
    rules = set()
    for rule in grammar.ast[2]:
        if rule[0] == 'rule' and not rule[1].startswith('%'):
            grammar.rules[rule[1]] = rule[2][0]
            rules.add(rule[1])
    for rule in grammar.rules:
        if rule not in rules:
            grammar.ast[2].append(['rule', rule, [grammar.rules[rule]]])


class Grammar:
    def __init__(self, ast):
        self.ast = ast
        self.comment = None
        self.rules = collections.OrderedDict()
        self.pragmas = []
        self.starting_rule = None
        self.tokens = set()
        self.whitespace = None
        self.assoc = {}
        self.prec = {}
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

        has_starting_rule = False
        for n in self.ast[2]:
            if n[1].startswith('%'):
                self.pragmas.append(n)
                if n[1] in ('%token', '%tokens'):
                    for t in n[2][0][2][0][2]:
                        assert t[0] == 'apply'
                        self.tokens.add(t[1])
                continue

            if not has_starting_rule:
                self.starting_rule = n[1]
                has_starting_rule = True
            self.rules[n[1]] = n[2][0]


class OperatorState:
    def __init__(self):
        self.prec_ops = {}
        self.rassoc = set()
        self.choices = {}


def analyze(ast, rewrite_filler=True):
    """Analyze and optimize the AST.

    This runs any static analysis we can do over the grammars and
    optimizes what we can. Raises AnalysisError if there are any errors.
    """

    # Do whatever analysis we can do.
    g = Grammar(ast)
    a = _Analyzer(g)
    a.analyze()

    # Now optimize and rewrite the AST as needed.
    _rewrite_recursion(g)
    if rewrite_filler:
        _rewrite_filler(g)
    _rewrite_singles(g)
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
    'scat',
    'scons',
    'strcat',
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

        self.comment = None
        self.errors = []
        self.rules = set()
        self.scopes = []
        self.tokens = set()
        self.whitespace = None
        self.assoc = {}
        self.prec = {}
        self.current_prec = 0

    def analyze(self):
        assert self.grammar.ast[0] == 'rules'

        # First figure out the names of all the rules so we can check
        # them as we walk the tree.
        self.rules = set(
            n[1]
            for n in self.grammar.ast[2]
            if n[0] == 'rule' and not n[1].startswith('%')
        )

        for node in self.grammar.ast[2]:
            assert node[0] == 'rule'
            rule_name = node[1]
            if rule_name[0] == '%':
                self._handle_pragma(node)
                continue
            for n in node[2]:
                self.walk(n)

        self.grammar.comment = self.comment
        self.grammar.whitespace = self.whitespace
        self.grammar.assoc = self.assoc
        self.grammar.prec = self.prec

        if self.errors:
            raise AnalysisError(self.errors)

    def walk(self, node):  # pylint: disable=too-many-statements
        ty = node[0]

        if ty == 'seq':
            self._handle_seq(node)
            return

        if ty == 'apply':
            if node[1] not in self.rules and node[1] not in ('any', 'end'):
                self.errors.append(f'Unknown rule "{node[1]}"')
        if ty == 'e_qual':
            if node[2][1][0] == 'e_call':
                assert node[2][0][0] == 'e_var'
                name = node[2][0][1]
                if name not in BUILTIN_FUNCTIONS:
                    self.errors.append(f'Unknown function "{name}" called')
                # Now skip over the var so we don't treat it as an actual var.
                for n in node[2][1:]:
                    self.walk(n)
                return

        if ty == 'e_var':
            if node[1] not in self.scopes[-1] and node[1][0] != '$':
                self.errors.append(f'Unknown variable "{node[1]}" referenced')

        for n in node[2]:
            self.walk(n)

    def _handle_pragma(self, node):
        rule_name = node[1]
        assert len(node[2]) == 1
        choice = node[2][0]
        assert choice[0] == 'choice'

        if rule_name in ('%token', '%tokens'):
            for subnode in choice[2]:
                assert subnode[0] == 'seq'
                for expr in subnode[2]:
                    assert expr[0] == 'apply'
                    token = expr[1]
                    if token in self.rules:
                        self.tokens.add(token)
                    else:
                        self.errors.append(f'Unknown token rule "{token}"')
        elif rule_name == '%whitespace':
            self.whitespace = choice
        elif rule_name == '%comment':
            self.comment = choice
        elif rule_name == '%prec':
            for c in choice[2]:
                assert c[0] == 'seq'
                for t in c[2]:
                    assert t[0] == 'lit'
                    self.prec[t[1]] = self.current_prec
                self.current_prec += 2
        else:
            assert rule_name == '%assoc'
            assert len(node[2]) == 1
            choice = node[2][0]
            assert choice[0] == 'choice'
            assert len(choice[2]) == 1
            seq = choice[2][0]
            assert seq[0] == 'seq'
            assert len(seq[2]) == 2
            assert seq[2][0][0] == 'lit'
            operator = seq[2][0][1]
            assert seq[2][1][0] == 'apply'
            direction = seq[2][1][1]
            assert direction in ('left', 'right')
            self.assoc[operator] = direction

    def _handle_seq(self, node):
        # Figure out what, if any, variables are being bound in this
        # sequence so that we can ensure that only bound variables
        # are being dereferenced in e_var nodes.
        self.scopes.append([])
        vs = set()
        for i, n in enumerate(node[2], start=1):
            if n[0] in ('action', 'equals', 'pred'):
                self._vars_needed(n[2][0], i, vs)
        for i, n in enumerate(node[2], start=1):
            name = f'${i}'
            if n[0] == 'label' and n[1][0] == '$':
                self.errors.append(
                    f'"{name}" is a reserved variable name '
                    'and cannot be explicitly defined'
                )
            if name in vs and (n[0] != 'label' or n[1] != name):
                node[2][i - 1] = ['label', name, [n]]

        for n in node[2]:
            if n[0] == 'label':
                self.scopes[-1].append(n[1])
            self.walk(n)

        self.scopes.pop()

    def _vars_needed(self, node, max_num, vs):
        ty = node[0]
        if ty == 'e_var':
            if node[1][0] == '$':
                num = int(node[1][1:])
                if num >= max_num:
                    self.errors.append(
                        f'Unknown variable "{node[1]}" referenced'
                    )
                else:
                    vs.add(node[1])
        elif ty in ('e_arr', 'e_call'):
            for n in node[2]:
                self._vars_needed(n, max_num, vs)
        elif ty in ('e_getitem', 'e_paren'):
            self._vars_needed(node[2][0], max_num, vs)
        elif ty in ('e_plus', 'e_minus'):
            self._vars_needed(node[2][0], max_num, vs)
            self._vars_needed(node[2][1], max_num, vs)
        elif ty in ('e_qual',):
            for n in node[2]:
                self._vars_needed(n, max_num, vs)
        elif ty in ('e_const', 'e_lit', 'e_num'):
            pass
        else:  # pragma: no cover
            assert False, f'Unexpected AST node type: {ty}'


class Visitor:
    def __init__(self, grammar):
        self.grammar = grammar

    def visit_pre(self, node):  # pragma: no cover
        return node, False

    def process(self):  # pragma: no cover
        pass

    def visit_post(self, node, results):
        return [node[0], node[1], results]


def walk(node, visitor):
    if node[0] == 'pragma':
        return node
    assert len(node) == 3
    pre, stop = visitor.visit_pre(node)
    if stop:
        return pre
    r = []
    for n in pre[2]:
        sn = walk(n, visitor)
        r.append(sn)
    node = visitor.visit_post(pre, r)
    return node


def _rewrite_singles(grammar):
    grammar.ast = walk(grammar.ast, _SinglesVisitor(grammar))

    # Any filler rules won't have been part of the AST, so we need to
    # rewrite them separately.
    for rule in ('_comment', '_filler', '_whitespace'):
        if rule in grammar.rules:
            grammar.rules[rule] = walk(
                grammar.rules[rule], _SinglesVisitor(grammar)
            )
    _update_rules(grammar)


class _SinglesVisitor(Visitor):
    def visit_pre(self, node):
        if node[0] in ('choice', 'seq') and len(node[2]) == 1:
            return self.visit_pre(node[2][0])
        return node, False


def _rewrite_recursion(grammar):
    """Rewrite the AST to insert leftrec and operator nodes as needed."""
    for node in grammar.ast[2]:
        if node[0] == 'pragma':
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
                choices[i] = ['leftrec', '%s#%d' % (name, i + 1), [choice]]


def _check_operator(grammar, name, choices):
    if len(choices) == 1:
        return None
    operators = []
    for choice in choices[:-1]:
        assert choice[0] == 'seq'
        if len(choice[2]) not in (3, 4):
            return None
        if choice[2][0] != ['label', '$1', [['apply', name, []]]] and choice[
            2
        ][0] != ['apply', name, []]:
            return None
        if choice[2][1][0] != 'lit' or choice[2][1][1] not in grammar.prec:
            return None
        operator = choice[2][1][1]
        prec = grammar.prec[operator]
        if choice[2][2] != ['label', '$3', [['apply', name, []]]] and choice[
            2
        ][2] != ['apply', name, []]:
            return None
        if len(choice[2]) == 4 and choice[2][3][0] != 'action':
            return None
        operators.append(['op', [operator, prec], [choice]])
    choice = choices[-1]
    if len(choice[2]) != 1:
        return None
    return ['choice', None, [['operator', name, operators], choices[-1]]]


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
    if ty == 'seq':
        for subnode in node[2]:
            if subnode[0] == 'lit':
                return False
            r = _check_lr(name, subnode, grammar, seen)
            if r:
                return r
        return False
    if ty == 'choice':
        return any(_check_lr(name, n, grammar, seen) for n in node[2])
    if ty in (
        'count',
        'ends_in',
        'label',
        'not',
        'not_one',
        'opt',
        'paren',
        'plus',
        'run',
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
        'lit',
        'pred',
        'range',
        'regexp',
        'set',
        'unicat',
    ), (
        'unexpected AST node type %s' % ty  # pragma: no cover
    )
    return False


def _rewrite_filler(grammar):
    if not grammar.comment and not grammar.whitespace:
        return

    # Compute the transitive closure of all the token rules.
    _TokenVisitor(grammar).process()

    # Now rewrite any literals, tokens, or 'end' to be filler nodes.
    _FillerVisitor(grammar).process()

    _update_rules(grammar)
    new_rules = []
    for rule in grammar.ast[2]:
        if rule[1] in ('%whitespace', '%comment'):
            continue
        new_rules.append(rule)
    grammar.ast[2] = new_rules
    grammar.comment = None
    grammar.whitespace = None


class _TokenVisitor(Visitor):
    def __init__(self, grammar):
        super().__init__(grammar)
        self.rules_to_process = grammar.tokens.copy()
        self.rules_processed = set()

    def process(self):
        while self.rules_to_process:
            rule = self.rules_to_process.pop()
            self.rules_processed.add(rule)
            walk(self.grammar.rules[rule], self)
        self.grammar.tokens = self.rules_processed

    def visit_pre(self, node):
        if node[0] == 'apply':
            rule_name = node[1]
            if (
                rule_name not in self.rules_processed
                and rule_name not in BUILTIN_RULES
            ):
                self.rules_to_process.add(rule_name)
        return node, False


class _FillerVisitor(Visitor):
    def visit_pre(self, node):
        fnode = ['apply', '_filler', []]

        if node[0] == 'rule' and node[1] in self.grammar.tokens:
            return node, True
        if node[0] == 'seq':
            children = []
            for child in node[2]:
                if self.should_fill(child):
                    children.append(fnode)
                    children.append(child)
                else:
                    sn = walk(child, self)
                    children.append(sn)
            return (['seq', None, children], True)
        if self.should_fill(node):
            return ['paren', None, [self.fill(node)]], True
        return node, False

    def process(self):
        _add_filler_rules(self.grammar)
        self.grammar.ast = walk(self.grammar.ast, self)

    def should_fill(self, node):
        if node[0] in ('escape', 'lit', 'range', 'regexp', 'set'):
            return True
        if node[0] == 'apply' and (
            node[1] == 'end' or node[1] in self.grammar.tokens
        ):
            return True
        return False

    def fill(self, node):
        return ['seq', None, [['apply', '_filler', []], node]]


def _add_filler_rules(grammar):
    if grammar.whitespace:
        grammar.rules['_whitespace'] = grammar.whitespace
    if grammar.comment:
        grammar.rules['_comment'] = grammar.comment
    if grammar.whitespace and grammar.comment:
        if (
            grammar.whitespace[0] == 'regexp'
            and grammar.comment[0] == 'regexp'
        ):
            grammar.rules['_filler'] = [
                'regexp',
                f'(({grammar.whitespace[1]})|({grammar.comment[1]}))*',
                [],
            ]
        else:
            grammar.rules['_filler'] = [
                'star',
                None,
                [
                    [
                        'choice',
                        None,
                        [
                            ['apply', '_whitespace', []],
                            ['apply', '_comment', []],
                        ],
                    ],
                ],
            ]
    elif grammar.comment:
        if grammar.comment[0] == 'regexp':
            grammar.rules['_filler'] = [
                'regexp',
                f'({grammar.comment[1]})*',
                [],
            ]
        else:
            grammar.rules['_filler'] = [
                'star',
                None,
                [['apply', '_comment', []]],
            ]
    else:
        assert grammar.whitespace
        if grammar.whitespace[0] == 'regexp':
            grammar.rules['_filler'] = [
                'regexp',
                f'({grammar.whitespace[1]})*',
                [],
            ]
        else:
            grammar.rules['_filler'] = [
                'star',
                None,
                [['apply', '_whitespace', []]],
            ]


def rewrite_subrules(
    grammar, rule_fmt='r_{rule}', subrule_fmt='s_{rule}_{counter}'
):
    sr = _SubRuleRewriter(grammar, rule_fmt, subrule_fmt)
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
        # TODO: rewrite grammar.ast

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
        return [node[0], node[1], subnodes]

    def _split1(self, node):
        return [node[0], node[1], [self._make_subrule(node[2][0])]]

    def _can_inline(self, node) -> bool:
        return node[0] not in (
            'choice',
            'count',
            'not',
            'opt',
            'plus',
            'regexp',
            'set',
            'seq',
            'star',
        )

    def _make_subrule(self, child):
        subnode_rule = self._subrule()
        self._subrules[subnode_rule] = self._walk(child)
        return ['apply', subnode_rule, []]

    def _ty_apply(self, node):
        if node[1] in ('any', 'end'):
            self._grammar.needed_builtin_rules.add(node[1])
        return [node[0], self._rule_fmt.format(rule=node[1]), node[2]]

    def _ty_ends_in(self, node):
        self._grammar.needed_builtin_rules.add('any')
        return self._walkn(node)

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
        return [node[0], node[1], []]

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
