# Things TODO

* compiler.py: Figure out how to handle inlining methods more consistently
  in _compile so that we don't have the special-casing logic here. Same
  thing in analyzer.py rewrite_singles().

* compiler.py: Figure out how to handle blank lines at the end of a method
  better in _flatten().

* grammar_test.py: Figure out how to reject references to variables that
  weren't bound at compile/interpret time,
  see GrammarTest.test_error_on_unknown_var.

* interpreter.py: Figure out whether you can statically reject unknown
  rules (in _handle_apply).

* printer_test.py: Improve printer algorithm so that two choices with
  actions are not printed on a single line (see test_actions).

* printer_test.py: Improve printer algorithm so that it can pretty-print
  floyd.g and stay under 80 characters wide (see test_floyd).

* Replace `:x` bindings with `$1`, `$2`, and so on.
  - use `$0` for matching everything as an array?

* Use `\1` for "text matching $1.

* Replace `is_unicat('Ld') with \p{Ld} (to match regex syntax).

* Support regexp escapes like \d, \s, and so on.

* Ensure that only reserved rules start with underscores.
  - Ensure that only reserved identifiers in values start with underscores,
    too?

* Define `\.` as a synonym for `_any`, `\$` as a synonym for `_end`?

* Allow customizable functions that will override the builtins like
  `dict()` in the parsers.
  - Would it make sense to have something like this for the compiler
    as well?

* Add bounded qualifiers like `foo^3`, `foo^3+`, `foo^3,4` or something.

* Use `?{}` for semantic predicate instead of `?()`, or use `?<>` maybe?

* Maybe add `_pos` built-in rule (and _pos() built-in function), 
  `_text` built-in value.

* Implement support for automatic whitespace and comment insertion in
  grammars.
  - You end up with four kinds of things: whitespace, comments, tokens
    (or terminals)?, and nonterminals.
  - Whitespace and comments are only automatically inserted in
    nonterminals, not tokens.
  - Need some kind of better name for nonterminals. Rules?
  - Enforce that tokens can be expressed as regexps.

* Implement left recursion. 

* Figure out how to notate for associativity and precedence without
  having to encode it in the ordering of rules, e.g. so you can write
  `expr = expr '*' expr` rather than `expr = expr '*' add_expr`.
  - Also figure out how to implement it :).
