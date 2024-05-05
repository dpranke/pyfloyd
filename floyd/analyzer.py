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
import copy


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
    for rule in grammar.ast[2]:
        if rule[0] == 'rule':
            grammar.rules[rule[1]] = rule[2][0]


class Grammar:
    def __init__(self, ast):
        self.ast = ast
        self.comment = None
        self.comment_style = None
        self.rules = collections.OrderedDict()
        self.starting_rule = None
        self.tokens = set()
        self.whitespace = None
        self.whitespace_style = None

        has_starting_rule = False
        for n in self.ast[2]:
            if n[0] == 'rule':
                if not has_starting_rule:
                    self.starting_rule = n[1]
                    has_starting_rule = True
                self.rules[n[1]] = n[2][0]
            elif n[0] == 'pragma' and n[1] in ('token', 'tokens'):
                for t in n[2]:
                    self.tokens.add(t)


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
    _rewrite_singles(g)
    _rewrite_left_recursion(g)
    if rewrite_filler:
        _rewrite_filler(g)
    return g


BUILTIN_FUNCTIONS = (
    'cat',
    'dict',
    'float',
    'hex',
    'is_unicat',
    'itou',
    'join',
    'utoi',
    'xtoi',
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
        self.comment_style = None
        self.errors = []
        self.rules = set()
        self.scopes = []
        self.tokens = set()
        self.whitespace = None
        self.whitespace_style = None

    def analyze(self):
        self.rules = set(n[1] for n in self.grammar.ast[2] if n[0] == 'rule')
        self.walk(self.grammar.ast)
        self.grammar.comment = self.comment
        self.grammar.comment_style = self.comment_style
        self.grammar.whitespace = self.whitespace
        self.grammar.whitespace_style = self.whitespace_style

        self._check_pragmas()

        if self.errors:
            raise AnalysisError(self.errors)

    def walk(self, node):  # pylint: disable=too-many-statements
        ty = node[0]

        if ty == 'seq':
            # Figure out what, if any, variables are being bound in this
            # sequence so that we can ensure that only bound variables
            # are being dereferenced in ll_var nodes.
            self.scopes.append([])
            vs = set()
            for i, n in enumerate(node[2], start=1):
                if n[0] in ('action', 'pred'):
                    self._vars_needed(n[2][0], i, vs)
            for i, n in enumerate(node[2], start=1):
                name = f'${i}'
                if n[0] == 'label' and n[1][0] == '$':
                    self.errors.append(
                        (
                            f'"{name}" is a reserved variable name '
                            'and cannot be explicitly defined'
                        )
                    )
                if name in vs and (n[0] != 'label' or n[1] != name):
                    node[2][i - 1] = ['label', name, [n]]

            for n in node[2]:
                if n[0] == 'label':
                    self.scopes[-1].append(n[1])

        if ty == 'apply':
            if node[1] not in self.rules and node[1] not in ('any', 'end'):
                self.errors.append(f'Unknown rule "{node[1]}"')
        if ty == 'll_qual':
            if node[2][1][0] == 'll_call':
                name = node[2][0][1]
                if name not in BUILTIN_FUNCTIONS:
                    self.errors.append(f'Unknown function "{name}" called')
            else:
                self.walk(node[2][0])
        if ty == 'll_var':
            if node[1] not in self.scopes[-1] and node[1][0] != '$':
                self.errors.append(f'Unknown variable "{node[1]}" referenced')

        if ty in ('choice', 'll_arr', 'll_call', 'rules', 'seq'):
            for n in node[2]:
                self.walk(n)
        elif ty == 'pragma':
            if node[1] in ('token', 'tokens'):
                for n in node[2]:
                    if n in self.rules:
                        self.tokens.add(n)
                    else:
                        self.errors.append(f'Unknown token rule "{n}"')
            elif node[1] == 'whitespace_style':
                self.whitespace_style = node[2]
            elif node[1] == 'whitespace':
                self.whitespace = node[2][0]
            elif node[1] == 'comment_style':
                self.comment_style = node[2]
            else:
                assert node[1] == 'comment'
                self.comment = node[2][0]
        elif ty == 'rule':
            self.walk(node[2][0])
        elif ty in (
            'action',
            'label',
            'll_getitem',
            'll_paren',
            'not',
            'paren',
            'post',
            'pred',
        ):
            self.walk(node[2][0])
        elif ty in ('ll_plus', 'll_minus'):
            self.walk(node[2][0])
            self.walk(node[2][0])
        elif ty == 'll_qual':
            for n in node[2][1:]:
                self.walk(n)

        if ty == 'seq':
            self.scopes.pop()

    def _vars_needed(self, node, max_num, vs):
        ty = node[0]
        if ty == 'll_var':
            if node[1][0] == '$':
                num = int(node[1][1:])
                if num >= max_num:
                    self.errors.append(
                        f'Unknown variable "{node[1]}" referenced'
                    )
                else:
                    vs.add(node[1])
        elif ty in ('ll_arr', 'll_call'):
            for n in node[2]:
                self._vars_needed(n, max_num, vs)
        elif ty in ('ll_getitem', 'll_paren'):
            self._vars_needed(node[2][0], max_num, vs)
        elif ty in ('ll_plus', 'll_minus'):
            self._vars_needed(node[2][0], max_num, vs)
            self._vars_needed(node[2][1], max_num, vs)
        elif ty in ('ll_qual'):
            for n in node[2]:
                self._vars_needed(n, max_num, vs)
        elif ty in ('ll_const', 'll_lit', 'll_num'):
            pass
        else:  # pragma: no cover
            assert False, f'Unexpected AST node type: {ty}'

    def _check_pragmas(self):
        if self.whitespace_style and self.whitespace_style != 'standard':
            self.errors.append(
                'Unknown %%whitespace_style "%s"' % self.whitespace_style
            )
        if self.comment_style and self.comment_style not in (
            'C',
            'C++',
            'Java',
            'JavaScript',
            'Python',
            'shell',
        ):
            self.errors.append(
                'Unknown %%comment_style "%s"' % self.comment_style
            )

        if self.comment and self.comment_style:
            self.errors.append(
                "Can't set both comment and comment_style pragmas"
            )
        if self.whitespace and self.whitespace_style:
            self.errors.append(
                "Can't set both whitespace and whitespace_style pragmas"
            )


class Visitor:
    def __init__(self, grammar):
        self.grammar = grammar

    def visit_pre(self, node):  # pragma: no cover
        return node, True

    def process(self):  # pragma: no cover
        pass

    def visit_post(self, node, results):
        return [node[0], node[1], results]


def walk(node, visitor):
    if node[0] == 'pragma':
        return node
    assert len(node) == 3
    pre, keep_going = visitor.visit_pre(node)
    if not keep_going:
        return pre
    r = []
    for n in pre[2]:
        sn = walk(n, visitor)
        r.append(sn)
    node = visitor.visit_post(pre, r)
    return node


def _rewrite_singles(grammar):
    grammar.ast = walk(grammar.ast, _SinglesVisitor(grammar))
    _update_rules(grammar)


class _SinglesVisitor(Visitor):
    def visit_pre(self, node):
        if node[0] in ('choice', 'seq'):
            if len(node[2]) == 1 and node[2][0][0] != 'apply':
                return self.visit_pre(node[2][0])
        return node, True


def _rewrite_left_recursion(grammar):
    """Rewrite the AST to insert leftrec nodes as needed."""
    lr_rules = _check_for_left_recursion(grammar)
    new_rules = []
    for rule in grammar.ast[2]:
        if rule[1] in lr_rules:
            new_rule = [rule[0], rule[1], [['leftrec', rule[1], rule[2]]]]
        else:
            new_rule = rule
        new_rules.append(new_rule)
    grammar.ast = ['rules', None, new_rules]
    _update_rules(grammar)


def _check_for_left_recursion(grammar):
    """Returns a list of all potentially left-recursive rules."""
    lr_rules = set()
    for ty, name, children in grammar.ast[2]:
        if ty == 'pragma':
            continue
        seen = set()
        has_lr = _check_lr(name, children[0], grammar.rules, seen)
        if has_lr:
            lr_rules.add(name)
    return lr_rules


def _check_lr(name, node, rules, seen):
    # pylint: disable=too-many-branches
    ty = node[0]
    if ty == 'action':
        return False
    if ty == 'apply':
        if node[1] == name:
            return True  # Direct recursion.
        if node[1] in ('any', 'anything', 'end'):
            return False
        if node[1] in seen:
            # We've hit left recursion on a different rule, so, no.
            return False
        seen.add(node[1])
        return _check_lr(name, rules[node[1]], rules, seen)
    if ty == 'choice':
        return any(_check_lr(name, n, rules, seen) for n in node[2])
    if ty == 'empty':
        return False
    if ty == 'label':
        return _check_lr(name, node[2][0], rules, seen)
    if ty == 'lit':
        return False
    if ty == 'not':
        return _check_lr(name, node[2][0], rules, seen)
    if ty == 'paren':
        return _check_lr(name, node[2][0], rules, seen)
    if ty == 'post':
        return _check_lr(name, node[2][0], rules, seen)
    if ty == 'pred':
        return False
    if ty == 'range':
        return False
    if ty == 'seq':
        for subnode in node[2]:
            if subnode[0] == 'lit':
                return False
            r = _check_lr(name, subnode, rules, seen)
            if r:
                return r
        return False
    if ty == 'unicat':
        return False

    assert False, 'unexpected AST node type %s' % ty  # pragma: no cover


def _rewrite_filler(grammar):
    if (
        not grammar.comment
        and not grammar.comment_style
        and not grammar.whitespace
        and not grammar.whitespace_style
    ):
        return

    # Compute the transitive closure of all the token rules.
    _TokenVisitor(grammar).process()

    # Now rewrite any literals, tokens, or 'end' to be filler nodes.
    _FillerVisitor(grammar).process()

    _update_rules(grammar)


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
        return node, True


class _FillerVisitor(Visitor):
    def __init__(self, grammar):
        super().__init__(grammar)
        if grammar.whitespace_style == 'standard':
            grammar.whitespace = STANDARD_WHITESPACE
        if grammar.comment_style:
            if grammar.comment_style in ('Python', 'shell'):
                grammar.comment = BASH_COMMENT
            elif grammar.comment_style == 'C':
                grammar.comment = C_COMMENT
            else:
                assert grammar.comment_style in ('C++', 'Java', 'JavaScript')
                grammar.comment = CPP_COMMENT
        if grammar.whitespace:
            grammar.rules['_whitespace'] = grammar.whitespace
        if grammar.comment:
            grammar.rules['_comment'] = grammar.comment

    def visit_pre(self, node):
        if node[0] == 'range':
            return self._rewrite_with_filler(node), False
        if node[0] == 'lit':
            return self._rewrite_with_filler(node), False
        if node[0] == 'apply' and (
            node[1] in self.grammar.tokens or node[1] == 'end'
        ):
            return self._rewrite_with_filler(node), False
        if node[0] == 'rule' and node[1] in self.grammar.tokens:
            return node, False
        return node, True

    def process(self):
        self.grammar.ast = walk(self.grammar.ast, self)

    def _rewrite_with_filler(self, node):
        if self.grammar.whitespace and self.grammar.comment:
            subnode = [
                'choice',
                None,
                [
                    ['apply', '_whitespace', []],
                    ['apply', '_comment', []],
                ],
            ]
        elif self.grammar.whitespace:
            subnode = ['apply', '_whitespace', []]
        else:
            subnode = ['apply', '_comment', []]

        return [
            'paren',
            None,
            [
                [
                    'seq',
                    None,
                    [
                        ['post', '*', [subnode]],
                        copy.deepcopy(node),
                    ],
                ]
            ],
        ]


# (' '|'\n'|'\r'|'\t')*
STANDARD_WHITESPACE = [
    'choice',
    None,
    [
        ['lit', ' ', []],
        ['lit', '\r', []],
        ['lit', '\n', []],
        ['lit', '\t', []],
    ],
]


def _eol_comment(lit):
    # $lit (~'\n' any)*
    return [
        'seq',
        None,
        [
            ['lit', lit, []],
            [
                'post',
                '*',
                [
                    [
                        'seq',
                        None,
                        [
                            ['not', None, [['lit', '\n', []]]],
                            ['apply', 'any', []],
                        ],
                    ]
                ],
            ],
        ],
    ]


BASH_COMMENT = _eol_comment('#')


# '/*' (~'*/' any)* '*/'
C_COMMENT = [
    'seq',
    None,
    [
        ['lit', '/*', []],
        [
            'post',
            '*',
            [
                [
                    'seq',
                    None,
                    [
                        ['not', None, [['lit', '*/', []]]],
                        ['apply', 'any', []],
                    ],
                ],
            ],
        ],
        ['lit', '*/', []],
    ],
]


CPP_COMMENT = ['choice', None, [_eol_comment('//'), C_COMMENT]]
