# pyfloyd

A parsing framework and parser generator for Python.

## Getting set up.

1. Install `uv` via whatever system-specific magic you need (e.g.,
   `brew install uv` on a Mac w/ Homebrew).
2. Run `./run devenv` to create a virtualenv at `//.venv` with
   all of the tools needed to do development (and with `pyfloyd` installed
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

* v0.19.0 (2024-11-18)
    * Clean up handling of external values in grammars and add more
      error checking.
    * Clean up the way the language to use when generating code is
      selected.
* v0.18.3 (2024-11-17)
    * Remove dependencies on `build`, `twine`, just use `uv build` and
      `uv publish`.
* v0.18.2 (2024-11-17)
    * Fix .gitignore.
* v0.18.1 (2024-11-18)
    * Update README.md.
* v0.18.0 (2024-11-17)
    * First release from `pyfloyd`. Renames everything and moves the
      package directory under src/.
* v0.17.4 (2024-11-17)
    * More cleanup - hopefully final release from `floyd-python`
* v0.17.3 (2024-11-17)
    * More cleanup
* v0.17.2 (2024-11-17)
    * More cleanup
* v0.17.0 (2024-11-17)
    * Remove code from `floyd-python` repo.
* v0.16.0 (2024-11-17)
    * Tons of cleanup, move to new syntax. I'm too lazy to document all of
      the changes from v0.15.0 to here. This is intended to be the last
      release of this project under this name; work will continue under
      the name `pyfloyd`.
* v0.15.0 (2024-07-05)
    * Add a JavaScript back end. As a part of this I've changed the GitHub
      CI config to install a specific version of Node so that the new
      JS codepaths are tested properly.
* v0.14.0 (2024-06-30)
    * Move a lot of the logic from python_compiler.py to a new pass in
      analyzer.py. Now python_compiler is very simple and you can start
      to see how it can be converted to something in a DSL like
      StringTemplate. This also will make it much easier to share logic
      between different compilers.
* v0.13 (2024-06-29)
    * Rework the way subrules are generated and named to be much less
      cryptic. Now rules result in methods named `_r_{rule}_` and
      subrules methods named `_s_{rule}_{i}` where i is a series of
      consecutive integers named in a depth first manner.
* v0.12 (2024-06-29)
    * Significantly rework the generated parser so that it is less like
      a set of parser combinators (self._star() and so on) and more like
      code that you'd write inline by hand. This appears to produce a
      parser close to 2x faster for 1.33x more code.
* v0.11 (2024-06-22)
    * Rework the API significantly. Now the generated parser API is a single
      `parse()` function and a data type for the return value (`Result`),
      and the public API functions are called `compile()` instead of
      `compile_parser()` and `generate()` instead of `generate_parser()`.
    * Add typing hints to everything.
    * Add lots more documentation of the API.
* v0.10.2 (2024-06-22)
    * Update test to use 79 cols instead of 80.
* v0.10.1 (2024-06-22)
    * Change formatter to default to 79 cols and regen/reformat.
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
