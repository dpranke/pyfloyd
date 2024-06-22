# floyd-python

A parsing framework and parser generator for Python.

**Note the Python package name is `floyd`, not `floyd-python`.
`floyd-python` is the name on PyPI.**

## Getting set up.

1. Install `uv` via whatever system-specific magic you need (e.g.,
   `brew install uv` on a Mac w/ Homebrew).
2. Run `./run devenv` to create a virtualenv at `//.venv` with
   all of the tools needed to do development (and with `floyd` installed
   as an editable Python project.
3. Run `source ./.venv/bin/activate` to activate the environment and pick
   up the tools.

## Running the tests

Get set up as per the above, and then run `./run tests`.

There are other commands to `run` to do other things like lint and
format the code. `./run --help` is your friend to find out more.

## Publishing a version

1. Run `./run build`
2. Run `./run publish --test]` or `./run publish --prod` to upload to PyPI.
   If you pass `--test`, the package will be uploaded to TestPyPI instead
   of the production instance.

## Version History / Release Notes

* v0.10.0 (2024-06-22)
    * Clean up compiler code, rework how inlining methods works. At this
      point the compiler code is probably about as reasonably clean and
      fast as the inlining approach can be.
* v0.9.0 (2024-05-19)
    * get operator expressions working: you can now declare the precedence
      and associativity of different operators in an expression and they
      will be handled correctly. Note that there is a fair amount of
      special-casing logic for this so that only some of the expressions
      you might think would work will actually work. It's also unclear
      how well this will play with memoization.
* v0.8.0 (2024-05-19)
    * get left association in expressions that are both left- and
      right-recursive working properly.
* v0.7.0 (2024-05-05)
   * Add support for `?{...}` for semantic predicates and `{...}` for
     semantic actions in addition to `?( ... )` and `-> ...`. For now,
     both syntaxes will be supported.
* v0.6.0
   * This version number was skipped.
* v0.5.0 (2024-05-04)
   * Get automatic whitespace and comment insertion working. The
     two collectively are known as "filler".
   * You can now declare "tokens" that can consist of compound expressions
     that will not have filler interleaved.
   * Add support for positional labels in addition to named labels, i.e.
     you can write an expression as `num '+' num -> $1 + $3` in addition
     to `num:l '+' num:r -> l + r`. Both syntaxes will be supported for
     now.
   * Do much more semantic analysis to catch a broader set of errors.
   * Add support for unicode character classes via `\p{X}`.
   * Turn `--memoize` and `--main` off by default in floyd.tool.
   * Got left recursion working.
   * Added type hints to the API.
* v0.4.0
    * This version number was skipped.
* v0.3.0 (2024-04-02)
    * Changed the interpreter so that it no longer relies on runtime
      compilation.
* v0.2.0 (2024-03-31)
    * 100% test coverage.
    * Code is clean and ready for new work.
    * Add docs/goals.md to describe what I'm hoping to accomplish with
      this project.
    * Add docs/todos.md to capture everything I'm planning to fix or
      change.
* v0.1.0 (2024-03-25)
    * Copy over working code from glop v0.7.0. This copies only the code
      needed to run things, and a couple of grammars that can be used
      for hand-testing things. This does not add any tests, since I'm
      likely going to rework all of that. The code is as-is as close to
      the working glop code as I can keep it, except for updated formatting
      and copyright info. `check` and `lint` are unhappy, the `coverage`
      numbers are terrible, and we probably need to regenerate the floyd
      parser as well.
* v0.0.5 (2024-03-24)
    * There's a pattern forming.
* v0.0.4 (2024-03-24)
    * Actually bump the version this time.
* v0.0.3 (2024-03-24)
    * Fix typos and bugs found after v0.0.2 was tagged :).
* v0.0.2 (2024-03-24)
    * Fix typos found after v0.0.1 was tagged :).
* v0.0.1 (2024-03-24)
    * Initial skeleton of the project uploaded to GitHub. There is nothing
      project-specific about this project except for the name and
      description.
