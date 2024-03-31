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


class Analyzer:
    def __init__(self):
        pass

    def analyze(self, ast):
        if ast[0] != 'rules':
            ast = ['rules', ast]
        assert ast[0] == 'rules' and any(n[0] == 'rule' for n in ast[1])
        ast = self.rewrite_singles(ast)
        return Grammar(ast)

    def rewrite_singles(self, node):
        if node[0] == 'rules':
            return [node[0], [self.rewrite_singles(n) for n in node[1]]]
        if node[0] == 'rule':
            return [node[0], node[1], self.rewrite_singles(node[2])]
        if node[0] in ('choice', 'seq'):
            if len(node[1]) == 1:
                return self.rewrite_singles(node[1][0])
            return [node[0], [self.rewrite_singles(n) for n in node[1]]]
        if node[0] == 'paren':
            return [node[0], self.rewrite_singles(node[1])]
        if node[0] in ('label', 'post'):
            return [node[0], self.rewrite_singles(node[1]), node[2]]
        return node
