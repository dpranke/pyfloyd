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


class Grammar:
    def __init__(self, ast):
        self.ast = ast
        self.starting_rule = ast[1][0][1]
        self.rules = collections.OrderedDict((n[1], n[2]) for n in ast[1])


def analyze(ast):
    if ast[0] != 'rules':
        ast = ['rules', ast]
    assert ast[0] == 'rules' and any(n[0] == 'rule' for n in ast[1])
    ast = _rewrite_singles(ast)
    ast = _rewrite_left_recursion(ast)
    return Grammar(ast)


def _rewrite_singles(node):
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
    for _, name, body in ast[1]:
        rules[name] = body
    for _, name, body in ast[1]:
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

    assert False, 'unexpected AST node type %s' % ty  # pragma: no cover
