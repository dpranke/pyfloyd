# Changes

This doc attempts to keep a history of the more prominent changes
to the project. For now I'm starting way late in the game, but
perhaps at some point I'll go back and backfill things.

* v0.27.0 (2025-06-16)
  - Make multiline strings dedented by default in datafiles. This removes
    the `d` tag (since it is no longer necessary) but adds an `i` tag to
    tell the datafile to leave the string indented.
  - Remove support for the `[==[foo]==]` long quote syntax. I don't think
    we need both this and `L'=='foo'=='`. It's somewhat debatable which
    syntax is more aesthetically pleasing, but the former was overloading
    the meaning of '[' and ']', which never seemed like a great idea.

* v0.26.0 (2025-06-10)
  - Added the ability for a grammar/parser to call out to functions
    provided by the caller. A function is declared as an `extern`
    (although there is as yet no typechecking), and can override
    an existing implementation of a function. External functions
    are passed the parser object so that they can query parser state
    (or, I suppose, mutate it, though at this point that's probably
    a terrible idea).
  - Restructured the grammar.Node / AST classes to collapse everything
    to a single class, deleting a lot of code. Most of it was overhead
    that wasn't pulling its weight.
  - Modified the Floyd grammar to call an external `node()` function;
    this moves the actual construction of the syntax nodes out of the grammar
    and will make it easier to generate different kinds of syntax trees
    as needed. The first use of this is to add position information to
    each node. This allows us to report position information for semantic
    errors like unknown rules and variables.
  - Removed the hard-coded JavaScript code generator. Templates are the
    way going forward, but at least for now it seems like a good idea to
    have at least one non-template code generation mechanism for comparison.

* v0.25.0 (2025-06-08)
  - Codegen for the Go programming language is supported
  - The runtime now enforces basic typechecking during the semantic analysis
    phase, and exposes typing information for local variables to the
    code generators. Go only partially uses this, because of limitations
    (as I understand them) in the Go type system that prevent you from
    casting directly from `[]T` to `[]any` and back that make using
    proper types more awkward than just using `any` values.
  - Simplified the AST for postfix operations in a post-processing pass
    that converts an expr + a list of postfix exprs to a tree of binary
    expressions. This might actually be a case where it'd be better to
    use left recursion in the grammar; I haven't investigated that yet.
  - Cleaned up the formatting objects a fair amount and made them more
    generic.
  - Split out tests into different classes to (hopefully) make it easier
    to test things while bringing up a new code generation target.
  - Add `let` and `cond` fexprs to the Lisp interpreter. This makes it
    a lot easier to write more complicated template rules.

* v0.22.0dev0 (2025-05-31)
  - Code for the built-in functions is now generated from a datafile.
    This makes it easier to share code between the host implementation
    and code generation templates, and reduces a bunch of duplicated
    information. [//docs/functions.md](./functions.md) now exists as
    a readable summary of the builtin functions.
  - Made dedenting strings in datafiles work properly when text follows
    the quote marks on the first line, i.e.

        d = d"""foo
                bar"""

    Previously we didn't know the column number on the line in the file,
    so we couldn't actually be sure that things were aligned (or not).
