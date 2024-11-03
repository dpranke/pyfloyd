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

    def update_rules(self):
        # Update grammar.rules to match grammar.ast for rules in
        # grammar.ast and then append any new rules to grammar.ast.
        rules = set()
        for rule in self.ast[2]:
            if rule[0] == 'rule' and not rule[1].startswith('%'):
                self.rules[rule[1]] = rule[2][0]
                rules.add(rule[1])
        for rule in self.rules:
            if rule not in rules:
                self.ast[2].append(['rule', rule, [self.rules[rule]]])


class OperatorState:
    def __init__(self):
        self.prec_ops = {}
        self.rassoc = set()
        self.choices = {}


def analyze(ast, rewrite_filler: bool, rewrite_subrules: bool) -> Grammar:
    """Analyze and optimize the AST.

    This runs any static analysis we can do over the grammars and
    optimizes what we can. Raises AnalysisError if there are any errors.

    If `rewrite_filler` is True, and the grammar has %whitespace or
    %comment pragmas, the grammar will be rewritten to insert the
    filler rules and insert the filler nodes where appropriate.
    You want this when either interpreting or compiling the grammar, but
    (usually) not when pretty-printing it. You might want this if you
    wanted to rewrite the grammar to expand out the filler rules when
    pretty-printing.

    If `rewrite_subrules` is True, any rule subnodes that can't really be
    inlined when generating code will be extracted out into their own rules.
    You want this when generating code, but not when pretty-printing the
    grammar. Do not set this when interpreting the grammar, because
    the built-in rules for 'any' and 'end' will be renamed and interpreting
    likely won't work as a result.
    """

    g = Grammar(ast)

    # Find whatever errors we can.
    a = _Analyzer(g)
    a.check_pragmas()
    a.check_identifiers()
    if a.errors:
        raise AnalysisError(a.errors)

    # Rewrite the AST to insert leftrec and operator nodes as needed.
    _rewrite_recursion(g)

    if rewrite_filler:
        # Insert filler rules and filler nodes.
        _rewrite_filler(g)

    # Rewrite any choice or seq nodes that only have one child.
    _rewrite_singles(g)

    if rewrite_subrules:
        # Extract subnodes into their own rules to make codegen easier.
        # Not needed when just interpreting the grammar, and not wanted
        # when printing the grammar.
        _rewrite_subrules(g)

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
        assert self.grammar.ast[0] == 'rules'

        self.assoc = {}
        self.comment = None
        self.current_prec = 0
        self.errors = []
        self.prec = {}
        self.rule_names = set(
            n[1]
            for n in self.grammar.ast[2]
            if n[0] == 'rule' and not n[1].startswith('%')
        )
        self.tokens = set()
        self.whitespace = None

    def check_pragmas(self):
        # Initialize all the data structures from the pragmas.
        # Will still use pragmas in subsequent checks.
        for node in self.grammar.ast[2]:
            if node[1].startswith('%'):
                self._check_pragma(node)
        self.grammar.comment = self.comment
        self.grammar.whitespace = self.whitespace
        self.grammar.assoc = self.assoc
        self.grammar.prec = self.prec

    def _check_pragma(self, node):
        rule_name = node[1]
        choice = node[2][0]

        if rule_name in ('%token', '%tokens'):
            for subnode in choice[2]:
                for expr in subnode[2]:
                    token = expr[1]
                    if token in self.rule_names:
                        self.tokens.add(token)
                    else:
                        self.errors.append(f'Unknown token rule "{token}"')
        elif rule_name == '%whitespace':
            self.whitespace = choice
        elif rule_name == '%comment':
            self.comment = choice
        elif rule_name == '%prec':
            for c in choice[2]:
                for t in c[2]:
                    self.prec[t[1]] = self.current_prec
                self.current_prec += 2
        else:
            choice = node[2][0]
            seq = choice[2][0]
            operator = seq[2][0][1]
            direction = seq[2][1][1]
            self.assoc[operator] = direction

    def check_identifiers(self):
        # Check for unknown rules, functions, and variables. Also check
        # for variables that are declared but not used.
        for node in self.grammar.ast[2]:
            if node[1].startswith('%'):
                continue
            self._check_identifiers(node)

    def _check_identifiers(self, node):
        ty = node[0]
        if ty == 'apply':
            if node[1] not in self.rule_names and node[1] not in (
                'any',
                'end',
            ):
                self.errors.append(f'Unknown rule "{node[1]}"')
        if ty != 'seq':
            for n in node[2]:
                self._check_identifiers(n)
            return

        # Figure out what, if any, variables are being bound in this
        # sequence so that we can ensure that only bound variables
        # are being dereferenced in e_var nodes.
        referenced_vs = set()
        labelled_vs = set()
        for i, n in enumerate(node[2], start=1):
            if n[0] in ('action', 'equals', 'pred'):
                self._vars_needed(n[2][0], i, referenced_vs)

        # Check for whether any $X fields are explicitly declared
        # (which is an error), and add label nodes for all of the
        # needed positional bindings.
        for i, n in enumerate(node[2], start=1):
            name = f'${i}'
            if n[0] == 'label':
                if n[1][0] == '$':
                    self.errors.append(
                        f'"{n[1]}" is a reserved variable name '
                        'and cannot be explicitly defined'
                    )
                else:
                    if n[1] not in referenced_vs:
                        self.errors.append(f'Unused variable "{n[1]}" defined')
                    else:
                        labelled_vs.add(n[1])
            if name in referenced_vs:
                node[2][i - 1] = ['label', name, [n]]
                labelled_vs.add(name)
            self._check_identifiers(n)

        for v in referenced_vs.difference(labelled_vs):
            if v not in BUILTIN_FUNCTIONS:
                self.errors.append(f'Unknown variable "{v}" referenced')

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
            else:
                vs.add(node[1])
        if ty == 'e_qual' and node[2][1][0] == 'e_call':
            name = node[2][0][1]
            if name not in BUILTIN_FUNCTIONS:
                self.errors.append(f'Unknown function "{name}" called')
            # Skip over the function name so we don't misinterpret it
            # as a variable.
            for n in node[2][1:]:
                self._vars_needed(n, max_num, vs)
            return

        for n in node[2]:
            self._vars_needed(n, max_num, vs)


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
    """Rewrite the grammar to insert filler rules and nodes, and unset
    %whitespace and %comment."""
    if not grammar.comment and not grammar.whitespace:
        return

    # Compute the transitive closure of all the token rules.
    _collect_tokens(grammar, grammar.ast)

    # Add in the _whitespace, _comment, and _filler rules.
    _add_filler_rules(grammar)

    # Now rewrite all the rules to insert the filler nodes.
    grammar.ast = _add_filler_nodes(grammar, grammar.ast)
    grammar.update_rules()

    # And strip out the %whitespace, %comment, and %token(s) pragmas.
    grammar.ast[2] = [
        rule
        for rule in grammar.ast[2]
        if rule[1] not in ('%whitespace', '%comment', '%token', '%tokens')
    ]
    grammar.comment = None
    grammar.whitespace = None
    grammar.tokens = set()
    grammar.pragmas = [
        n
        for n in grammar.pragmas
        if n[1] not in ('%whitespace', '%comment', '%token', '%tokens')
    ]


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
    grammar.ast[2].append(['rule', '_filler', [grammar.rules['_filler']]])
    if grammar.whitespace:
        grammar.ast[2].append(['rule', '_whitespace', [grammar.whitespace]])
    if grammar.comment:
        grammar.ast[2].append(['rule', '_comment', [grammar.comment]])


def _add_filler_nodes(grammar, node):
    def should_fill(node):
        if node[0] in ('escape', 'lit', 'range', 'regexp', 'set'):
            return True
        if node[0] == 'apply' and (
            node[1] == 'end' or node[1] in grammar.tokens
        ):
            return True
        return False

    if node[0] == 'pragma':
        return node
    if node[0] == 'rule' and node[1] in grammar.tokens:
        # By definition we don't want to insert filler into token rules.
        return node
    if node[0] == 'rule' and node[1] in ('_comment', '_filler', '_whitespace'):
        # These *are* the filler rules, so we don't want to insert filler
        # into them.
        return node
    if node[0] == 'seq':
        children = []
        for child in node[2]:
            if should_fill(child):
                children.append(['apply', '_filler', []])
                children.append(child)
            else:
                sn = _add_filler_nodes(grammar, child)
                children.append(sn)
        return ['seq', None, children]
    if should_fill(node):
        return [
            'paren',
            None,
            [['seq', None, [['apply', '_filler', []], node]]],
        ]

    return [node[0], node[1], [_add_filler_nodes(grammar, n) for n in node[2]]]


def _rewrite_singles(grammar):
    """Replace any choice or seq nodes in the AST with only one child as
    that child."""

    def walk(node):
        if node[0] in ('choice', 'seq') and len(node[2]) == 1:
            return walk(node[2][0])
        return [node[0], node[1], [walk(n) for n in node[2]]]

    grammar.ast = walk(grammar.ast)
    grammar.update_rules()


def _rewrite_subrules(grammar):
    # Extract subrules from rules as needed to be able to generate
    # code properly.
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
            rules.append(['rule', rule, [self._grammar.rules[rule]]])
        self._grammar.ast = ['rules', None, rules]

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
            'run',
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
