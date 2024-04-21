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
        self.starting_rule = None
        for n in ast[1]:
            if n[0] == 'rule':
                self.starting_rule = n[1]
                break
        self.tokens = set()
        self.rules = collections.OrderedDict()
        for n in ast[1]:
            if n[0] == 'pragma' and n[1] == 'tokens':
                for t in n[2:]:
                    self.tokens.add(t)
            elif n[0] == 'rule':
                self.rules[n[1]] = n[2]
        self.whitespace = None
        self.comment = None

def analyze(ast):
    """Analyze and optimize the AST.

    This runs any static analysis we can do over the grammars and
    optimizes what we can. Raises AnalysisError if there are any errors.
    """

    # Do whatever analysis we can do.
    a = _Analyzer()
    a.analyze(ast)

    # Now optimize and rewrite the AST as needed.
    ast = _rewrite_singles(ast)
    ast = _rewrite_left_recursion(ast)
    return Grammar(ast)


class _Analyzer:
    def __init__(self):
        self.rules = set()
        self.tokens = set()
        self.scopes = []
        self.errors = []

    def analyze(self, ast):
        self.rules = set(n[1] for n in ast[1] if n[0] == 'rule')
        self.walk(ast)
        if self.errors:
            raise AnalysisError(self.errors)

    def walk(self, node):
        ty = node[0]

        if ty == 'seq':
            # Figure out what, if any, variables are being bound in this
            # sequence so that we can ensure that only bound variables
            # are being dereferenced in ll_var nodes.
            self.scopes.append([])
            vs = set()
            for i, n in enumerate(node[1], start=1):
                if n[0] in ('action', 'pred'):
                    self._vars_needed(n[1], i, vs)
            for i, n in enumerate(node[1], start=1):
                name = f'${i}'
                if n[0] == 'label' and n[2][0] == '$':
                    self.errors.append(
                        (
                            f'"{name}" is a reserved variable name '
                            'and cannot be explicitly defined'
                        )
                    )
                if name in vs and (n[0] != 'label' or n[2] != name):
                    node[1][i - 1] = ['label', n, name]

            for n in node[1]:
                if n[0] == 'label':
                    self.scopes[-1].append(n[2])

        if ty == 'apply':
            if node[1] not in self.rules and node[1] not in ('any', 'end'):
                self.errors.append(f'Unknown rule "{node[1]}"')
        if ty == 'll_qual':
            assert node[1][0] == 'll_var'
            name = node[1][1]
            if node[2][0][0] == 'll_call':
                if name not in (
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
                ):
                    self.errors.append(f'Unknown function "{name}" called')
            else:
                self.walk(node[1])
        if ty == 'll_var':
            if node[1] not in self.scopes[-1] and node[1][0] != '$':
                self.errors.append(f'Unknown variable "{node[1]}" referenced')

        if ty in ('choice', 'll_arr', 'll_call', 'rules', 'seq'):
            for n in node[1]:
                self.walk(n)
        elif ty == 'pragma':
            if node[1] in ('token', 'tokens'):
                for n in node[2]:
                    if n in self.rules:
                        self.tokens.add(n)
                    else:
                        self.errors.append(f'Unknown token rule "{n}"')
            elif node[1] == 'whitespace':
                self.whitespace = self.node[2]
            else:
                assert node[1] == 'comment'
                self.comment = self.node[2]
        elif ty == 'rule':
            self.walk(node[2])
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
            self.walk(node[1])
        elif ty in ('ll_plus', 'll_minus'):
            self.walk(node[1])
            self.walk(node[2])
        elif ty == 'll_qual':
            for n in node[2]:
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
            for n in node[1]:
                self._vars_needed(n, max_num, vs)
        elif ty in ('ll_getitem', 'll_paren'):
            self._vars_needed(node[1], max_num, vs)
        elif ty in ('ll_plus', 'll_minus'):
            self._vars_needed(node[1], max_num, vs)
            self._vars_needed(node[2], max_num, vs)
        elif ty in ('ll_qual'):
            for n in node[2]:
                self._vars_needed(n, max_num, vs)
        elif ty in ('ll_const', 'll_lit', 'll_num'):
            pass
        else:  # pragma: no cover
            assert False, f'Unexpected AST node type: {ty}'


def _rewrite_singles(node):
    """Collapse seqs and choices with only one expr to just the expr."""
    if node[0] == 'rules':
        return [node[0], [_rewrite_singles(n) for n in node[1]]]
    if node[0] == 'rule':
        return [node[0], node[1], _rewrite_singles(node[2])]
    if node[0] in ('choice', 'seq'):
        # TODO: the apply check stops top-level sequences with only
        # an apply from being inlined, messing up the compiler
        # code generation. Figure out how to not have to special
        # case this.
        if len(node[1]) == 1 and node[1][0][0] != 'apply':
            return _rewrite_singles(node[1][0])
        return [node[0], [_rewrite_singles(n) for n in node[1]]]
    if node[0] == 'paren':
        return [node[0], _rewrite_singles(node[1])]
    if node[0] in ('label', 'post'):
        return [node[0], _rewrite_singles(node[1]), node[2]]
    return node


def _rewrite_left_recursion(ast):
    """Rewrite the AST to insert leftrec nodes as needed."""
    lr_rules = _check_for_left_recursion(ast)
    new_rules = []
    for rule in ast[1]:
        if rule[1] in lr_rules:
            new_rules.append([rule[0], rule[1], ['leftrec', rule[2], rule[1]]])
        else:
            new_rules.append(rule)
    return ['rules', new_rules]


def _check_for_left_recursion(ast):
    """Returns a list of all potentially left-recursive rules."""
    lr_rules = set()
    rules = {}
    for ty, name, body in ast[1]:
        if ty == 'pragma':
            continue
        rules[name] = body
    for ty, name, body in ast[1]:
        if ty == 'pragma':
            continue
        seen = set()
        has_lr = _check_lr(name, body, rules, seen)
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
        return any(_check_lr(name, n, rules, seen) for n in node[1])
    if ty == 'empty':
        return False
    if ty == 'label':
        return _check_lr(name, node[1], rules, seen)
    if ty == 'lit':
        return False
    if ty == 'not':
        return _check_lr(name, node[1], rules, seen)
    if ty == 'paren':
        return _check_lr(name, node[1], rules, seen)
    if ty == 'post':
        return _check_lr(name, node[1], rules, seen)
    if ty == 'pred':
        return False
    if ty == 'range':
        return False
    if ty == 'seq':
        for subnode in node[1]:
            if subnode[0] == 'lit':
                return False
            r = _check_lr(name, subnode, rules, seen)
            if r:
                return r
        return False
    if ty == 'unicat':
        return False

    assert False, 'unexpected AST node type %s' % ty  # pragma: no cover
