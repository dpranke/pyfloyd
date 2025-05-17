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

from pyfloyd import grammar as gram


class AnalysisError(Exception):
    """Raised when something fails one or more static analysis checks."""

    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        s = 'Errors were found:\n  '
        s += '\n  '.join(error for error in self.errors)
        s += '\n'
        return s


def analyze(ast, rewrite_subrules: bool) -> gram.Grammar:
    """Analyze and optimize the AST.

    This runs any static analysis we can do over the grammars and
    optimizes what we can. Raises AnalysisError if there are any errors.
    """

    g = gram.Grammar(ast)

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

    _compute_local_vars(g)

    # TODO: Figure out how to statically analyze predicates to
    # catch ones that don't return booleans, so that we don't need
    # to worry about runtime exceptions where possible.
    def _exception_needed(node):
        if node.t == 'pred':
            return True
        return any(_exception_needed(c) for c in node.ch)

    g.exception_needed = _exception_needed(g.ast)

    # Figure out which nodes can fail, etc.
    g.update_node(g.ast)

    g.needed_builtin_rules = sorted(set(g.needed_builtin_rules))
    g.needed_builtin_functions = sorted(set(g.needed_builtin_functions))
    g.unicodedata_needed = (
        g.unicat_needed or 'unicode_lookup' in g.needed_builtin_functions
    )
    g.seeds_needed = g.leftrec_needed or g.operator_needed

    return g


class _Analyzer:
    def __init__(self, grammar: gram.Grammar):
        self.grammar = grammar
        assert self.grammar.ast.t == 'rules'
        self.errors = []
        self.current_prec = 0
        self.current_rule = None

    def add_pragmas(self):
        for rule in self.grammar.ast.rules:
            self.current_rule = rule.name
            if rule.name[0] == '%':
                self.check_pragma(rule)
                continue

    def run_checks(self):
        for rule in self.grammar.ast.rules:
            if rule.name.startswith('_'):
                self.errors.append(
                    f'Illegal rule name "{rule.name}": '
                    'names starting with an "_" are reserved'
                )
            self.current_rule = rule.name
            if rule.name[0] == '%':
                continue
            self.check_for_unknown_rules(rule)
            self.check_for_unknown_functions(rule)
            self.check_positional_vars(rule)
            self.check_named_vars(rule)

    def check_pragma(self, rule):
        pragma = rule.name
        choice = rule.child

        if rule.name == '%externs':
            self._collect_externs(rule)
        elif rule.name == '%tokens':
            self._collect_idents(self.grammar.tokens, rule)
            for t in self.grammar.tokens:
                if t not in self.grammar.rules:
                    self.errors.append(f'Unknown token rule "{t}"')
        elif rule.name == '%whitespace':
            self.grammar.whitespace = choice
        elif rule.name == '%comment':
            self.grammar.comment = choice
        elif rule.name == '%prec':
            operators = set()
            for c in rule.child.ch:
                self._collect_operators(operators, c)
                for op in operators:
                    self.grammar.prec[op] = self.current_prec
                self.current_prec += 2
        elif rule.name == '%assoc':
            choice = rule.child
            seq = choice.child
            operator = seq.ch[0][1]
            direction = seq.ch[1][1]
            self.grammar.assoc[operator] = direction
        else:
            self.errors.append(f'Unknown pragma "{pragma}"')

    def _collect_externs(self, n):
        assert n.child.t == 'choice'
        for choice in n.child.ch:
            assert choice[0] == 'seq'
            assert choice.ch[0].t == 'apply'
            key = choice.ch[0].rule_name
            assert choice.ch[1].t == 'action'
            assert choice.ch[1].child.t == 'e_const'
            assert choice.ch[1].child.v in ('true', 'false')
            value = choice.ch[1].child.v == 'true'
            self.grammar.externs[key] = value

    def _collect_idents(self, s, node):
        if node.t == 'apply':
            s.add(node.rule_name)
        for c in node.ch:
            self._collect_idents(s, c)

    def _collect_operators(self, operators, node):
        if node.t == 'lit':
            operators.add(node.v)
            return
        if node.t == 'apply':
            if node.rule_name not in self.grammar.rules:
                self.errors.append(f'Unknown rule "{node.rule_name}"')
                return
            self._collect_operators(
                operators, self.grammar.rules[node.rule_name]
            )
            return
        if node.t in ('rule', 'choice', 'seq'):
            for c in node.ch:
                self._collect_operators(operators, c)
            return
        self.errors.append(f'Unexpected AST node type {node.t} in %prec')

    def check_for_unknown_rules(self, node):
        if (
            node.t == 'apply'
            and node.rule_name not in self.grammar.rules
            and node.rule_name not in ('any', 'end')
        ):
            self.errors.append(f'Unknown rule "{node.rule_name}"')
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

        labels_needed = set()
        for i, c in enumerate(node.ch, start=1):
            name = f'${i}'
            if c.t == 'label':
                if c.name[0] == '$':
                    self.errors.append(
                        f'"{c.name}" is a reserved variable name '
                        'and cannot be explicitly defined'
                    )
                self.check_positional_vars(c.child)
            if c.t in ('action', 'equals', 'pred'):
                self._check_positional_var_refs(c.child, i, labels_needed)

        # Now define all the positional vars we need.
        for i, c in enumerate(node.ch, start=1):
            name = f'${i}'
            if name in labels_needed:
                node.ch[i - 1] = gram.Label(name, c)

    def _check_positional_var_refs(self, node, current_index, labels_needed):
        if node.t == 'e_var':
            if node.v[0] == '$':
                num = int(node.v[1:])
                if num >= current_index:
                    self.errors.append(
                        f'Variable "{node.v}" referenced before '
                        'it was available'
                    )
                else:
                    # We don't want to think of unknown variables as
                    # referenced, so just keep track of the known ones.
                    labels_needed.add(node.v)

        if node.t == 'e_qual' and node.ch[1].t == 'e_call':
            assert node.ch[0].t == 'e_var'
            # Skip over the first child as it is a function name.
            start = 1
        else:
            start = 0
        for n in node.ch[start:]:
            self._check_positional_var_refs(n, current_index, labels_needed)

    def check_for_unknown_functions(self, node):
        if node.t == 'e_qual' and node.ch[1].t == 'e_call':
            function_name = node.ch[0].v
            if function_name not in gram.BUILTIN_FUNCTIONS:
                self.errors.append(
                    f'Unknown function "{function_name}" called'
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
                    if c.name[0] != '$':
                        labels[c.name] = c
                        local_labels[c.name] = c
                    self._check_named_vars(
                        c.child, labels, local_labels, references
                    )
                else:
                    self._check_named_vars(c, labels, local_labels, references)

            for v in set(local_labels.keys()) - set(references):
                self.errors.append(f'Variable "{v}" never used')

            # Now remove any variables that were defined in this scope.
            for v in set(local_labels.keys()).difference(
                set(outer_labels.keys())
            ):
                if v in references:
                    references.remove(v)
                del labels[v]
            return

        if node.t == 'e_var':
            var_name = node.v
            if var_name not in local_labels:
                if var_name in labels:
                    node.outer_scope = True
                    labels[var_name].outer_scope = True
                    self.grammar.needed_operators.append('lookup')
                    self.grammar.lookup_needed = True
                    self.grammar.outer_scope_rules.add(self.current_rule)
            else:
                if var_name in labels and labels[var_name].outer_scope:
                    node.outer_scope = True
            if var_name in labels:
                references.add(var_name)
            elif var_name in self.grammar.externs:
                pass
            elif not var_name[0] == '$':
                self.errors.append(f'Unknown variable "{var_name}" referenced')

        if node.t == 'e_qual' and node.ch[1].t == 'e_call':
            # Skip over names that are functions.
            start = 1
        else:
            start = 0
        for c in node.ch[start:]:
            self._check_named_vars(c, labels, local_labels, references)


def _rewrite_scopes(grammar):
    def rewrite_node(node):
        for i, c in enumerate(node.ch):
            node.ch[i] = rewrite_node(c)
        if node.t == 'seq' and any(c.t == 'label' for c in node.ch):
            return gram.Scope([node])
        return node

    for rule in grammar.ast.rules:
        if rule.name in grammar.outer_scope_rules:
            rule.child = rewrite_node(rule.child)


def _rewrite_recursion(grammar):
    """Rewrite the AST to insert leftrec and operator nodes as needed."""
    for rule in grammar.ast.rules:
        if rule.name[0] == '%':
            continue
        name = rule.name
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
                node_name = '%s#%d' % (name, i + 1)
                choices[i] = gram.Leftrec(
                    node_name,
                    choice,
                )
                choices[i].left_assoc = (
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
        if choice.ch[0] != gram.Label('$1', gram.Apply(name)) and choice.ch[
            0
        ] != gram.Apply(name):
            return None
        if choice.ch[1].t != 'lit' or choice.ch[1].v not in grammar.prec:
            return None
        operator = choice.ch[1].v
        prec = grammar.prec[operator]
        if choice.ch[2] != gram.Label('$3', gram.Apply(name)) and choice.ch[
            2
        ] != gram.Apply(name):
            return None
        if len(choice.ch) == 4 and choice.ch[3].t != 'action':
            return None
        if has_scope:
            choice = gram.Scope([choice])
        operators.append(gram.Op(operator, prec, choice))
    choice = choices[-1]
    if len(choice[2]) != 1:
        return None
    return gram.Choice([gram.Operator(name, operators), choices[-1]])


def _check_lr(rule_name, node, grammar, seen):
    # pylint: disable=too-many-branches
    if node.t == 'apply':
        if node.rule_name == rule_name:
            seen.add(rule_name)
            return True  # Direct recursion.
        if node.rule_name in ('any', 'anything', 'end'):
            return False
        if node.rule_name in seen:
            # We've hit left recursion on a different rule, so, no.
            return False
        seen.add(node.rule_name)
        return _check_lr(
            rule_name, grammar.rules[node.rule_name], grammar, seen
        )
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
        'unexpected AST node type %s' % node.t  # pragma: no cover
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
    if node.t == 'rules':
        for rule in node.rules:
            if rule.name in grammar.tokens:
                _collect_tokens(grammar, rule)
        return

    if node.t == 'apply' and node.rule_name not in gram.BUILTIN_RULES:
        grammar.tokens.add(node.rule_name)

    for c in node.ch:
        _collect_tokens(grammar, c)


def _add_filler_rules(grammar):
    if grammar.whitespace:
        grammar.tokens.add('%whitespace')
    if grammar.comment:
        grammar.tokens.add('%comment')
    filler = None
    if grammar.whitespace and grammar.comment:
        if grammar.whitespace.t == 'regexp' and grammar.comment.t == 'regexp':
            filler = gram.Regexp(
                f'(({grammar.whitespace.v})|({grammar.comment.v}))*',
            )
        else:
            filler = gram.Star(
                gram.Choice(
                    [gram.Apply('%whitespace'), gram.Apply('%comment')]
                )
            )
    elif grammar.comment:
        if grammar.comment.t == 'regexp':
            filler = gram.Regexp(f'({grammar.comment.v})*')
        else:
            filler = gram.Star(gram.Apply('%comment'))
    elif grammar.whitespace:
        if grammar.whitespace.t == 'regexp':
            filler = gram.Regexp(f'({grammar.whitespace.v})*')
        else:
            filler = gram.Star(gram.Apply('%whitespace'))
    if filler:
        grammar.rules['%filler'] = gram.Choice([filler])


def _add_filler_nodes(grammar, node):
    def should_fill(node):
        if node.t in ('escape', 'lit', 'range', 'regexp', 'set'):
            return True
        if node.t == 'apply' and node.rule_name in (
            '%comment',
            '%filler',
            '%whitespace',
        ):
            return False
        if node.t == 'apply' and (
            node.rule_name == 'end' or node.rule_name in grammar.tokens
        ):
            return True
        if node.t == 'empty':
            return True
        return False

    if node.t == 'rule' and node.name.startswith('%'):
        # Don't mess with the pragmas.
        return node
    if node.t == 'rule' and node.name in grammar.tokens:
        # By definition we don't want to insert filler into token rules.
        return node
    if node.t == 'rule' and node.name in (
        '%comment',
        '%filler',
        '%whitespace',
    ):
        # These *are* the filler rules, so we don't want to insert filler
        # into them.
        return node
    if node.t == 'seq':
        children = []
        if len(children) == 1 and node.ch[0].t == 'action':
            children.append(gram.Apply('%filler'))
        for c in node.ch:
            if should_fill(c):
                children.append(gram.Apply('%filler'))
                children.append(c)
            else:
                sn = _add_filler_nodes(grammar, c)
                children.append(sn)
        return gram.Seq(children)
    if should_fill(node):
        return gram.Paren(gram.Seq([gram.Apply('%filler'), node]))

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
            rules.append(gram.Rule(rule, self._grammar.rules[rule]))
        self._grammar.ast = gram.Rules(rules)

    def _subrule(self) -> str:
        self._counter += 1
        return self._subrule_fmt.format(
            rule_name=self._rule_name, counter=self._counter
        )

    def _subrule_key(self, s: str) -> int:
        return int(
            s.replace(
                's_{rule_name}_'.format(rule_name=self._rule_name), ''
            ).replace('_', '')
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
            'run',
            'set',
            'seq',
            'star',
        )

    def _make_subrule(self, child):
        subnode_rule = self._subrule()
        self._subrules[subnode_rule] = self._walk(child)
        return gram.Apply(subnode_rule)

    def _ty_apply(self, node):
        if node.rule_name in ('any', 'end'):
            self._grammar.needed_builtin_rules.append(node.rule_name)
        return gram.Apply(self._rule_fmt.format(rule_name=node.rule_name))

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
        if node.ch[0].t == 'e_var' and node.ch[1].t == 'e_call':
            self._grammar.needed_builtin_functions.append(node.ch[0].v)
        return self._walkn(node)

    def _ty_not_one(self, node):
        self._grammar.needed_builtin_rules.append('any')
        return self._walkn(node)

    def _ty_operator(self, node):
        self._grammar.needed_operators.append('operator')
        self._grammar.operator_needed = True
        o = gram.OperatorState()
        prec_ops = {}
        for operator in node.ch:
            op, prec = operator.v
            subnode = operator.child
            prec_ops.setdefault(prec, []).append(op)
            if self._grammar.assoc.get(op) == 'right':
                o.rassoc.add(op)
            subnode_rule = self._subrule()
            o.choices[op] = subnode_rule
            self._subrules[subnode_rule] = self._walk(subnode)

        for prec in sorted(prec_ops):
            o.prec_ops[prec] = prec_ops[prec]
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
        self._grammar.needed_operators.append('regexp')
        self._grammar.re_needed = True
        return node

    def _ty_set(self, node):
        self._grammar.needed_operators.append('regexp')
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
        if node.t == 'apply' and node.rule_name.startswith('%'):
            node.rule_name = node.rule_name.replace('%', '_')
        for c in node.ch:
            _rewrite(c)

    new_rules = []
    for rule in grammar.ast.rules:
        if rule.name.startswith('%'):
            old_rule_name = rule.name
            if rule.name in ('%comment', '%whitespace', '%filler'):
                rule.name = rule.name.replace('%', '_')
                _rewrite(rule.child)
                new_rules.append(rule)
                grammar.rules[rule.name] = rule
            if old_rule_name in grammar.rules:
                del grammar.rules[old_rule_name]
        else:
            _rewrite(rule.child)
            new_rules.append(rule)
    grammar.ast.rules = new_rules


def _compute_local_vars(grammar):
    def _walk(node) -> set[str]:
        vs: set[str] = set()
        if node.t == 'seq':
            for c in node.ch:
                vs.update(_walk(c))
            node.vars = sorted(vs)
            return set()

        if node.t == 'label':
            vs.add(node.name)
        for c in node.ch:
            vs.update(_walk(c))
        return vs

    for rule in grammar.ast.rules:
        vs = _walk(rule.child)
        assert vs == set()
