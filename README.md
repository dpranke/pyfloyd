# floyd

A parser generator and interpreter framework for Python.

## Getting set up.

1. Install `uv` via whatever system-specific magic you need (e.g.,
   `brew install uv` on a Mac w/ Homebrew).
2. Run `./run devenv` to create a virtualenv at `//.venv` with
   all of the tools needed to do development (and with `floyd` installed
   as an editable Python project.
3. Run `source ./.venv/bin/activate` to activate the environment and pick up
   the tools.

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

* v0.0.4 (2024-03-24)
    * Actually bump the version this time.
* v0.0.3 (2024-03-24)
    * Fix typos and bugs found after v0.0.2 was tagged :).
* v0.0.2 (2024-03-24)
    * Fix typos found after v0.0.1 was tagged :).
* v0.0.1 (2024-03-24)
    * Initial skeleton of the project uploaded to GitHub. There is nothing
      project-specific about this project except for the name and description.
