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

from typing import Any

from pyfloyd import functions
from pyfloyd import grammar as m_grammar


def analyze(
    ast,
    rewrite_subrules: bool,
    for_pretty_printing: bool = False,
    rewrite_filler: bool = True,
    typecheck: bool = True,
    tokenize: bool = False,
) -> m_grammar.Grammar:
    """Analyze and optimize the AST.

    This runs any static analysis we can do over the grammars and
    optimizes what we can. Raises AnalysisError if there are any errors.
    """

    g = m_grammar.Grammar(ast)

    # Find whatever errors we can.
    a = _Analyzer(g)
    a.add_pragmas()

    # Add in the _whitespace, _comment, and _filler rules.
    if rewrite_filler:
        _add_filler_rules(g)

    if (tokenize or g.tokenize) and g.tokens:
        g.tokenize = True
        g.needed_operators.append('tok')
        _rewrite_rules_for_tokens(g)

    if for_pretty_printing:
        # Insert filler nodes, but otherwise don't do anything else, just
        # return.
        if rewrite_filler:
            _rewrite_filler(g)
        return g

    a.run_checks()
    if g.errors:
        return g

    # Rewrite quals from a list to a tree of getitems and calls.
    _rewrite_quals(g)

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
        if node.t == 'pred':
            return True
        return any(_exception_needed(c) for c in node.ch)

    g.exception_needed = _exception_needed(g.ast)

    # Do typechecking, figure out which nodes can fail, figure out which
    # nodes' values are used, etc.
    g.update_node(g.ast, typecheck)
    if g.errors:
        return g

    _compute_vars(g)

    g.needed_builtin_rules = sorted(set(g.needed_builtin_rules))
    g.needed_builtin_functions = sorted(set(g.needed_builtin_functions))
    g.needed_operators = sorted(set(g.needed_operators))
    g.unicodedata_needed = (
        g.unicat_needed or 'ulookup' in g.needed_builtin_functions
    )
    g.seeds_needed = g.leftrec_needed or g.operator_needed

    return g


class _Analyzer:
    def __init__(self, grammar: m_grammar.Grammar):
        self.grammar = grammar
        assert self.grammar.ast.t == 'rules'
        self.current_prec = 0
        self.current_rule = None

    def add_pragmas(self):
        for rule in self.grammar.ast.ch:
            self.current_rule = rule.v
            if rule.v[0] == '%':
                self.check_pragma(rule)
                continue

    def add_error(self, node, msg):
        if node.parser:
            # TODO: The column number might be slightly off at this point
            # because we're looking at the wrong node. Leave it out for now.
            # pylint: disable=protected-access
            lineno, _ = node.parser._o_offsets(node.pos)
            self.grammar.errors.append(f'{node.parser._path}:{lineno} {msg}')
        else:
            self.grammar.errors.append(msg)

    def run_checks(self):
        for rule in self.grammar.ast.ch:
            if rule.v.startswith('_'):
                self.grammar.errors.append(
                    f'Illegal rule name "{rule.v}": '
                    'names starting with an "_" are reserved'
                )
            self.current_rule = rule.v
            if rule.v[0] == '%' and rule.v not in ('%whitespace', '%comment'):
                continue
            self.check_for_unknown_rules(rule)
            self.check_for_unknown_functions(rule)
            self.check_positional_vars(rule)
            self.check_named_vars(rule)

    def check_pragma(self, rule):
        pragma = rule.v
        choice = rule.child

        if rule.v == '%externs':
            self._collect_externs(rule)
        elif rule.v == '%tokens':
            self._collect_idents(self.grammar.tokens, rule)
            for t in self.grammar.tokens:
                if t not in self.grammar.rules:
                    self.add_error(rule, f'Unknown token rule "{t}"')
        elif rule.v == '%whitespace':
            self.grammar.whitespace = choice
        elif rule.v == '%comment':
            self.grammar.comment = choice
        elif rule.v == '%prec':
            operators = set()
            for c in rule.child.ch:
                self._collect_operators(operators, c)
                for op in operators:
                    self.grammar.prec[op] = self.current_prec
                self.current_prec += 2
        elif rule.v == '%assoc':
            choice = rule.child
            seq = choice.child
            operator = seq.ch[0].v
            direction = seq.ch[1].v
            self.grammar.assoc[operator] = direction
        else:
            self.add_error(rule, f'Unknown pragma "{pragma}"')

    def _collect_externs(self, n):
        assert n.child.t == 'choice'
        for choice in n.child.ch:
            assert choice.t == 'seq'
            assert choice.ch[0].t == 'apply'
            key = choice.ch[0].v
            assert choice.ch[1].t == 'action'
            if (
                choice.ch[1].child.t == 'e_ident'
                and choice.ch[1].child.v == 'func'
            ):
                self.grammar.externs[key] = 'func'
            else:
                assert choice.ch[1].child.t == 'e_const'
                assert choice.ch[1].child.v in ('true', 'false', 'func')
                value = choice.ch[1].child.v == 'true'
                if choice.ch[1].child.v == 'func':
                    self.grammar.externs[key] = 'func'
                else:
                    self.grammar.externs[key] = value

    def _collect_idents(self, s, node):
        if node.t == 'apply':
            s.add(node.v)
        for c in node.ch:
            self._collect_idents(s, c)

    def _collect_operators(self, operators, node):
        if node.t == 'lit':
            operators.add(node.v)
            return
        if node.t == 'apply':
            if node.v not in self.grammar.rules:
                self.add_error(node, f'Unknown rule "{node.v}"')
                return
            self._collect_operators(operators, self.grammar.rules[node.v])
            return
        if node.t in ('rule', 'choice', 'seq'):
            for c in node.ch:
                self._collect_operators(operators, c)
            return
        self.add_error(node, f'Unexpected AST node type {node.t} in %prec')

    def check_for_unknown_rules(self, node):
        if (
            node.t == 'apply'
            and node.v not in self.grammar.rules
            and node.v not in ('any', 'end')
        ):
            self.add_error(node, f'Unknown rule "{node.v}"')
        for c in node.ch:
            self.check_for_unknown_rules(c)

    def check_positional_vars(self, node):
        """Checks that:
        - No one tries to define a positional var explicitly
          (e.g., `grammar = 'foo':$1` is bad).
        - Any reference to a positional var only happens after it would
          be defined  (e.g., `grammar = {$2}` is bad).
        And then rewrites the AST to insert label nodes for the needed
        positional vars.
        """
        if node.t != 'seq':
            for c in node.ch:
                self.check_positional_vars(c)
            return

        labels_needed = set()
        for i, c in enumerate(node.ch, start=1):
            name = f'${i}'
            if c.t == 'label':
                if c.v[0] == '$':
                    self.add_error(
                        c,
                        f'"{c.v}" is a reserved variable name '
                        'and cannot be explicitly defined',
                    )
                self.check_positional_vars(c.child)
            if c.t in (
                'count',
                'ends_in',
                'not',
                'not_one',
                'opt',
                'paren',
                'plus',
                'run',
                'star',
            ):
                self.check_positional_vars(c)
            if c.t in ('action', 'equals', 'pred'):
                self._check_positional_var_refs(c.child, i, labels_needed)

        # Now define all the positional vars we need.
        for i, c in enumerate(node.ch, start=1):
            name = f'${i}'
            if name in labels_needed:
                node.ch[i - 1] = m_grammar.Node('label', name, [c])

    def _check_positional_var_refs(self, node, current_index, labels_needed):
        if node.t == 'e_ident':
            if node.v[0] == '$':
                num = int(node.v[1:])
                if num >= current_index:
                    self.add_error(
                        node,
                        f'Variable "{node.v}" referenced before '
                        'it was available',
                    )
                else:
                    # We don't want to think of unknown variables as
                    # referenced, so just keep track of the known ones.
                    labels_needed.add(node.v)

        for n in node.ch:
            self._check_positional_var_refs(n, current_index, labels_needed)

    def check_for_unknown_functions(self, node):
        if node.t == 'e_qual' and node.ch[1].t == 'e_call':
            function_name = node.ch[0].v
            if (
                function_name not in functions.ALL
                and function_name not in self.grammar.externs
            ):
                self.add_error(
                    node, f'Unknown function "{function_name}" called'
                )
        for c in node.ch:
            self.check_for_unknown_functions(c)

    def check_named_vars(self, node):
        assert node.t == 'rule'
        labels = {}
        local_labels = {}
        references = set()
        self._check_named_vars(node, labels, local_labels, references)

    def _check_named_vars(self, node, labels, local_labels, references):
        if node.t == 'seq':
            outer_labels = labels.copy()
            local_labels = {}
            for c in node.ch:
                if c.t == 'label':
                    if c.v[0] != '$':
                        labels[c.v] = c
                        local_labels[c.v] = c
                    self._check_named_vars(
                        c.child, labels, local_labels, references
                    )
                else:
                    self._check_named_vars(c, labels, local_labels, references)

            for v in set(local_labels.keys()) - set(references):
                self.add_error(node, f'Variable "{v}" never used')

            # Now remove any variables that were defined in this scope.
            for v in set(local_labels.keys()).difference(
                set(outer_labels.keys())
            ):
                if v in references:
                    references.remove(v)
                del labels[v]
            return

        if node.t == 'e_ident':
            var_name = node.v
            if (var_name not in local_labels and var_name in labels) or (
                var_name in labels and labels[var_name].attrs.outer_scope
            ):
                node.attrs.outer_scope = True
                node.attrs.kind = 'outer'
                labels[var_name].attrs.outer_scope = True
                self.grammar.needed_operators.append('lookup')
                self.grammar.lookup_needed = True
                self.grammar.outer_scope_rules.add(self.current_rule)
                references.add(var_name)
            elif var_name in local_labels or var_name[0] == '$':
                node.attrs.kind = 'local'
                references.add(var_name)
            elif var_name in functions.ALL:
                node.attrs.kind = 'function'
                self.grammar.needed_builtin_functions.append(var_name)
            elif var_name in self.grammar.externs:
                node.attrs.kind = 'extern'
            else:
                self.add_error(
                    node, f'Unknown identifier "{var_name}" referenced'
                )

        for c in node.ch:
            self._check_named_vars(c, labels, local_labels, references)


def _rewrite_rules_for_tokens(grammar):
    for rule in grammar.ast.ch:
        if rule.v.startswith('%') and rule.v not in (
            '%whitespace',
            '%comment',
        ):
            continue
        rule.child = m_grammar.Node('rule_wrapper', rule.v, [rule.child])
        grammar.rules[rule.v] = rule


def _rewrite_quals(grammar):
    def rewrite_node(node):
        if node.t == 'e_qual':
            # A qual is a term plus a list of postfix expressions. We
            # need to turn it into a tree of binary expressions as some
            # languages may need to manipulate both the left and right
            # hand sides of the expression. To do this we need to basically
            # do a right fold over the list.
            r = node.ch[0]
            for i, c in enumerate(node.ch[1:]):
                if c.t == 'e_call':
                    r = m_grammar.Node(
                        'e_call_infix',
                        None,
                        [r] + [rewrite_node(gc) for gc in c.ch],
                    )
                elif c.t == 'e_getitem':
                    r = m_grammar.Node(
                        'e_getitem_infix', None, [r, rewrite_node(c.child)]
                    )
            return r
        for i, c in enumerate(node.ch):
            node.ch[i] = rewrite_node(c)
        return node

    for rule in grammar.ast.ch:
        rule.child = rewrite_node(rule.child)


def _rewrite_scopes(grammar):
    def rewrite_node(node):
        for i, c in enumerate(node.ch):
            node.ch[i] = rewrite_node(c)
        if node.t == 'seq' and any(c.t == 'label' for c in node.ch):
            return m_grammar.Node('scope', None, [node])
        return node

    for rule in grammar.ast.ch:
        if rule.v in grammar.outer_scope_rules:
            rule.child = rewrite_node(rule.child)


def _rewrite_recursion(grammar):
    """Rewrite the AST to insert leftrec and operator nodes as needed."""
    for rule in grammar.ast.ch:
        if rule.v[0] == '%':
            continue
        name = rule.v
        if rule.child.t == 'rule_wrapper':
            assert rule.child.child.t == 'choice'
            choices = rule.child.child.ch
        else:
            assert rule.child.t == 'choice'
            choices = rule.child.ch

        operator_node = _check_operator(grammar, name, choices)
        if operator_node:
            name = operator_node.ch[0].v
            rule.ch = [operator_node]
            grammar.rules[name] = operator_node
            continue

        for i, choice in enumerate(choices):
            seen = set()
            has_lr = _check_lr(name, choice, grammar, seen)
            if has_lr:
                grammar.leftrec_rules.update(seen)
                node_name = name + '#' + str(i + 1)
                choices[i] = m_grammar.Node('leftrec', node_name, [choice])
                choices[i].attrs.left_assoc = (
                    grammar.assoc.get(node_name, 'left') == 'left'
                )


def _check_operator(grammar, name, choices):
    if len(choices) == 1:
        return None
    operators = []
    for choice in choices[:-1]:
        has_scope = choice.t == 'scope'
        if has_scope:
            # TODO: is this the right logic?
            choice = choice.child
        assert choice.t == 'seq'
        if len(choice.ch) not in (3, 4):
            return None
        if choice.ch[0] != m_grammar.Node(
            'label', '$1', [m_grammar.Node('apply', name)]
        ) and choice.ch[0] != m_grammar.Node('apply', name):
            return None
        if choice.ch[1].t != 'lit' or choice.ch[1].v not in grammar.prec:
            return None
        operator = choice.ch[1].v
        prec = grammar.prec[operator]
        if choice.ch[2] != m_grammar.Node(
            'label', '$3', [m_grammar.Node('apply', name)]
        ) and choice.ch[2] != m_grammar.Node('apply', name):
            return None
        if len(choice.ch) == 4 and choice.ch[3].t != 'action':
            return None
        if has_scope:
            choice = m_grammar.Node('scope', None, [choice])
        operators.append(m_grammar.Node('op', [operator, prec], [choice]))
    choice = choices[-1]
    if len(choice.ch) != 1:
        return None
    return m_grammar.Node(
        'choice',
        None,
        [m_grammar.Node('operator', name, operators), choices[-1]],
    )


def _check_lr(rule_name, node, grammar, seen):
    # pylint: disable=too-many-branches
    if node.t == 'apply':
        if node.v == rule_name:
            seen.add(rule_name)
            return True  # Direct recursion.
        if node.v in ('any', 'anything', 'end'):
            return False
        if node.v in seen:
            # We've hit left recursion on a different rule, so, no.
            return False
        seen.add(node.v)
        return _check_lr(rule_name, grammar.rules[node.v], grammar, seen)
    if node.t in ('lit', 'ends_in', 'not_one', 'plus', 'unicat'):
        return False
    if node.t == 'seq':
        for c in node.ch:
            if c.t == 'lit':
                return False
            r = _check_lr(rule_name, c, grammar, seen)
            if r is not None:
                return r
        return False
    if node.t == 'choice':
        for c in node.ch:
            r = _check_lr(rule_name, c, grammar, seen)
            if r is not None:
                return r
        return None
    if node.t in ('opt', 'star'):
        return None
    if node.t in (
        'count',
        'label',
        'not',
        'opt',
        'paren',
        'rule',
        'rule_wrapper',
        'run',
        'scope',
        'star',
    ):
        return _check_lr(rule_name, node.child, grammar, seen)

    # If we get here, either this is an unknown AST node type, or
    # it is one we think we shouldn't be able to reach, like an
    # operator node or a e_* node.
    assert node.t in (
        'action',
        'empty',
        'equals',
        'leftrec',
        'pred',
        'range',
        'regexp',
        'set',
    ), (
        'unexpected AST node type `{node.t}`'  # pragma: no cover
    )
    return False


def _rewrite_filler(grammar):
    """Rewrites the grammar to insert filler rules and nodes."""
    if not grammar.comment and not grammar.whitespace:
        return

    # Compute the transitive closure of all the token rules.
    grammar.subtokens = set(grammar.tokens)
    _collect_subtokens(grammar, grammar.ast)

    # Now rewrite all the rules to insert the filler nodes.
    grammar.ast = _add_filler_nodes(grammar, grammar.ast)
    grammar.update_rules()


def _collect_subtokens(grammar, node):
    # Collect the list of all rules reachable from this token rule:
    # all of them should be treated as tokens as well.
    if node.t == 'rules':
        for rule in node.ch:
            if rule.v in grammar.subtokens:
                _collect_subtokens(grammar, rule)
        return

    if node.t == 'apply' and node.v not in m_grammar.BUILTIN_RULES:
        grammar.subtokens.add(node.v)

    for c in node.ch:
        _collect_subtokens(grammar, c)


def _add_filler_rules(grammar):
    if grammar.whitespace:
        grammar.tokens.add('%whitespace')
    if grammar.comment:
        grammar.tokens.add('%comment')
    filler = None
    if grammar.whitespace and grammar.comment:
        if grammar.whitespace.t == 'regexp' and grammar.comment.t == 'regexp':
            filler = m_grammar.Node(
                'regexp',
                f'(({grammar.whitespace.v})|({grammar.comment.v}))*',
            )
        else:
            filler = m_grammar.Node(
                'star',
                None,
                [
                    m_grammar.Node(
                        'choice',
                        None,
                        [
                            m_grammar.Node('apply', '%whitespace'),
                            m_grammar.Node('apply', '%comment'),
                        ],
                    )
                ],
            )
    elif grammar.comment:
        if grammar.comment.t == 'regexp':
            filler = m_grammar.Node('regexp', f'({grammar.comment.v})*')
        else:
            filler = m_grammar.Node(
                'star', None, [m_grammar.Node('apply', '%comment')]
            )
    elif grammar.whitespace:
        if grammar.whitespace.t == 'regexp':
            filler = m_grammar.Node('regexp', f'({grammar.whitespace.v})*')
        else:
            filler = m_grammar.Node(
                'star', None, [m_grammar.Node('apply', '%whitespace')]
            )
    if filler:
        grammar.rules['%filler'] = m_grammar.Node(
            'run', None, [m_grammar.Node('choice', None, [filler])]
        )


def _add_filler_nodes(grammar, node):
    def should_fill(node):
        if node.t in ('escape', 'lit', 'range', 'regexp', 'set'):
            return True
        if node.t == 'apply' and node.v in (
            '%comment',
            '%filler',
            '%whitespace',
        ):
            return False
        if node.t == 'apply' and (node.v == 'end' or node.v in grammar.tokens):
            return True
        if node.t == 'empty':
            return True
        return False

    if node.t == 'rule' and node.v.startswith('%'):
        # Don't mess with the pragmas.
        return node
    if node.t == 'rule' and node.v in grammar.subtokens:
        # By definition we don't want to insert filler into token rules.
        return node
    if node.t == 'seq':
        children = []
        if len(children) == 1 and node.ch[0].t == 'action':
            children.append(m_grammar.Node('apply', '%filler'))
        for c in node.ch:
            if should_fill(c):
                children.append(m_grammar.Node('apply', '%filler'))
                children.append(c)
            else:
                sn = _add_filler_nodes(grammar, c)
                children.append(sn)
        return m_grammar.Node('seq', None, children)
    if should_fill(node):
        return m_grammar.Node(
            'paren',
            None,
            [
                m_grammar.Node(
                    'seq', None, [m_grammar.Node('apply', '%filler'), node]
                )
            ],
        )

    node.ch = [_add_filler_nodes(grammar, c) for c in node.ch]
    return node


def _rewrite_singles(grammar):
    """Replace any choice or seq nodes in the AST with only one child as
    that child."""

    def walk(node):
        if node.t in ('choice', 'seq') and len(node.ch) == 1:
            return walk(node.child)
        node.ch = [walk(c) for c in node.ch]
        return node

    grammar.ast = walk(grammar.ast)
    grammar.update_rules()


def _rewrite_subrules(grammar):
    """Extracts subrules from rules as needed to be able to generate
    code properly."""
    sr = _SubRuleRewriter(grammar, 'r_{rule_name}', 's_{rule_name}_{counter}')
    sr.rewrite()


class _SubRuleRewriter:
    def __init__(self, grammar, rule_fmt, subrule_fmt):
        self._grammar = grammar
        self._rule_fmt = rule_fmt
        self._subrule_fmt = subrule_fmt
        self._rule_name = None
        self._counter = 0
        self._methods = {}
        self._subrules = {}

    def rewrite(self):
        for rule_name, node in self._grammar.rules.items():
            self._rule_name = rule_name
            self._subrules = {}
            self._counter = 0
            new_node = self._walk(node)
            self._methods[self._rule_fmt.format(rule_name=rule_name)] = (
                new_node
            )
            subrules = sorted(self._subrules.keys(), key=self._subrule_key)
            for subrule in subrules:
                self._methods[subrule] = self._subrules[subrule]
        self._grammar.rules = self._methods
        rules = []
        for rule in self._grammar.rules:
            rules.append(
                m_grammar.Node('rule', rule, [self._grammar.rules[rule]])
            )
        self._grammar.ast = m_grammar.Node('rules', None, rules)

    def _subrule(self) -> str:
        self._counter += 1
        return self._subrule_fmt.format(
            rule_name=self._rule_name, counter=self._counter
        )

    def _subrule_key(self, s: str) -> int:
        return int(
            s.replace('s_' + self._rule_name + '_', '').replace('_', '')
        )

    def _walk(self, node):
        fn = getattr(self, f'_ty_{node.t}', None)
        if fn:
            return fn(node)  # pylint: disable=not-callable
        return self._walkn(node)

    def _walkn(self, node):
        subnodes = []
        for c in node.ch:
            if self._can_inline(c):
                subnodes.append(self._walk(c))
            else:
                subnodes.append(self._make_subrule(c))
        node.ch = subnodes
        return node

    def _split1(self, node):
        node.ch = [self._make_subrule(node.child)]
        return node

    def _can_inline(self, node) -> bool:
        return node.t not in (
            'choice',
            'count',
            'not',
            'opt',
            'plus',
            'regexp',
            'rule_wrapper',
            'run',
            'set',
            'seq',
            'star',
        )

    def _make_subrule(self, child):
        subnode_rule = self._subrule()
        self._subrules[subnode_rule] = self._walk(child)
        return m_grammar.Node('apply', subnode_rule)

    def _ty_apply(self, node):
        if node.v in ('any', 'end'):
            self._grammar.needed_builtin_rules.append(node.v)
        return m_grammar.Node('apply', self._rule_fmt.format(rule_name=node.v))

    def _ty_ends_in(self, node):
        self._grammar.needed_builtin_rules.append('any')
        return self._walkn(node)

    def _ty_equals(self, node):
        self._grammar.needed_operators.append('ch')
        self._grammar.needed_operators.append('str')
        self._grammar.ch_needed = True
        self._grammar.str_needed = True
        return node

    def _ty_leftrec(self, node):
        self._grammar.needed_operators.append('leftrec')
        self._grammar.leftrec_needed = True
        return self._split1(node)

    def _ty_lit(self, node):
        self._grammar.needed_operators.append('ch')
        self._grammar.ch_needed = True
        if len(node.v) > 1:
            self._grammar.needed_operators.append('str')
            self._grammar.str_needed = True
        return node

    def _ty_e_qual(self, node):
        return self._walkn(node)

    def _ty_not_one(self, node):
        self._grammar.needed_builtin_rules.append('any')
        return self._walkn(node)

    def _ty_operator(self, node):
        self._grammar.needed_operators.append('operator')
        self._grammar.operator_needed = True
        o = m_grammar.OperatorState()
        prec_ops = {}
        rassoc = set()
        for operator in node.ch:
            op, prec = operator.v
            subnode = operator.child
            prec_ops.setdefault(prec, []).append(op)
            if self._grammar.assoc.get(op) == 'right':
                rassoc.add(op)
            subnode_rule = self._subrule()
            o.choices[op] = subnode_rule
            self._subrules[subnode_rule] = self._walk(subnode)

        for prec in sorted(prec_ops):
            o.prec_ops[prec] = prec_ops[prec]
        o.rassoc = list(rassoc)
        self._grammar.operators[node.v] = o
        node.ch = []
        return node

    def _ty_paren(self, node):
        return self._split1(node)

    def _ty_range(self, node):
        self._grammar.needed_operators.append('range')
        self._grammar.range_needed = True
        return node

    def _ty_regexp(self, node):
        self._grammar.re_needed = True
        return node

    def _ty_set(self, node):
        self._grammar.re_needed = True
        return node

    def _ty_unicat(self, node):
        self._grammar.needed_operators.append('unicat')
        self._grammar.unicat_needed = True
        return node


def _rewrite_pragma_rules(grammar):
    # '%' is not a legal character to be in an identifier in most programming
    # languages, so we need to rewrite rule names containing '%' to something
    # else.
    def _rewrite(node):
        if node.t == 'apply' and node.v.startswith('%'):
            node.v = node.v.replace('%', '_')
        for c in node.ch:
            _rewrite(c)

    new_rules = []
    for rule in grammar.ast.ch:
        if rule.v.startswith('%'):
            old_rule_name = rule.v
            if rule.v in ('%comment', '%whitespace', '%filler'):
                rule.v = rule.v.replace('%', '_')
                _rewrite(rule.child)
                new_rules.append(rule)
                grammar.rules[rule.v] = rule
            if old_rule_name in grammar.rules:
                del grammar.rules[old_rule_name]
        else:
            _rewrite(rule.child)
            new_rules.append(rule)
    grammar.ast.ch = new_rules


def _compute_vars(grammar):
    def _walk(node) -> dict[str, Any]:
        vs: dict[str, Any] = {}
        if node.t == 'seq':
            for c in node.ch:
                vs.update(_walk(c))
            node.attrs.vars = vs
            return vs

        if node.t == 'label' and not node.attrs.outer_scope:
            vs[node.v] = node.type
        for c in node.ch:
            vs.update(_walk(c))
        return vs

    for rule in grammar.ast.ch:
        _walk(rule.child)
