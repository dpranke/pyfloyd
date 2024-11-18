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

from typing import Any, Dict, NamedTuple, Optional, Protocol, Tuple

from pyfloyd import analyzer
from pyfloyd.interpreter import Interpreter
from pyfloyd import parser
from pyfloyd.printer import Printer
from pyfloyd import generator
from pyfloyd.python_generator import PythonGenerator
from pyfloyd.javascript_generator import JavaScriptGenerator

Result = parser.Result

Externs = Optional[Dict[str, Any]]

Generator = generator.Generator
GeneratorOptions = generator.GeneratorOptions
DEFAULT_LANGUAGE = generator.DEFAULT_LANGUAGE
SUPPORTED_LANGUAGES = generator.SUPPORTED_LANGUAGES

_generators = {
    'javascript': JavaScriptGenerator,
    'python': PythonGenerator,
}
assert set(_generators.keys()) == set(generator.SUPPORTED_LANGUAGES)


class ParserInterface(Protocol):
    """The interface to a compiled parser.

    This represents the public interface of the object returned from
    `compile()`.
    """

    def parse(
        self,
        text: str,
        path: str = '<string>',
        externs: Externs = None,
    ) -> Result:
        """Parse a string and return a result.

        `text` is the string to parse.
        `path` is an optional parameter that can be used in error messages
               to reflect where the text came from, e.g., a file path.
        """


class CompiledResult(NamedTuple):
    """The result of `compile_parser()`.

    This represents the tuple of objects returned from `compile_parser()`.

    `parser` If not None, this is the parser object to use to parse strings.
             It will be something that implements the `ParserInterface`
             protocol.
    `err`    A string describing any error(s) in the grammar.

    Only one of `parser` and `err` will have a value, the other will be None.
    """

    parser: Optional[ParserInterface] = None
    err: Optional[str] = None
    pos: Optional[int] = None


def compile(  # pylint: disable=redefined-builtin
    grammar: str, path: str = '<string>', memoize: bool = False
) -> CompiledResult:
    """Compile the grammar into an object that can parse strings.

    This routine parses the provided grammar and returns an object
    that can parse strings according to the grammar.
    """
    result = parser.parse(grammar, path)
    if result.err:
        return CompiledResult(err=result.err, pos=result.pos)
    try:
        g = analyzer.analyze(
            result.val, rewrite_filler=True, rewrite_subrules=False
        )
        interpreter = Interpreter(g, memoize=memoize)
        return CompiledResult(interpreter, None)
    except analyzer.AnalysisError as e:
        return CompiledResult(None, str(e))


def generate(
    grammar: str,
    path: str = '<string>',
    options: Optional[GeneratorOptions] = None,
    externs: Externs = None,
) -> Result:
    """Generate the source code of a parser.

    This generates the text of a parser. The text will be a module
    with a public `Result` type and a public `parse()` function.

    `options.language` specifies the language to use for the generated
    parser. By default the language will be `DEFAULT_LANGUAGE`.

    If `options.main` is True, then the generated parser file will also have a
    `main()` function that is called if the text is invoked directly. (i.e.,
    the module can be run from the command line). The command line interface
    will take one optional argument that is the path to a file to parse; if the
    argument is missing or it is `'-'` then the parser will read from stdin
    instead. Any output will be written to stdout as a JSON string.  The actual
    interface to the `main()` routine contains a bunch of parameters that can
    all be substituted in for `sys.stdin`, `sys.stdout`, and `sys.argv` for
    testing purposes.

    If `options.memoize` is True, the parser will memoize (cache) the results
    of each combination of rule and position during the parse. For some
    grammars, this may provide significant speedups.

    `path` represents an optional string that can be included in error
    messages, e.g., as a path to the file containing the grammar.

    If successful the `.val` member of the result will be the source
    code for the parser. If the grammar had errors, the `.err` member of
    the result will describe the errors.
    """

    result = parser.parse(grammar, path)
    externs = externs or {}
    if result.err:
        return result
    try:
        grammar_obj = analyzer.analyze(
            result.val,
            rewrite_filler=True,
            rewrite_subrules=True,
        )
    except analyzer.AnalysisError as e:
        return Result(err=str(e))

    options = options or GeneratorOptions()
    gen: Generator
    cls = _generators.get(options.language.lower())
    if cls:
        gen = cls(grammar_obj, options)
        text = gen.generate()
        return Result(text)

    supp = ' and '.join(f'"{lang}"' for lang in SUPPORTED_LANGUAGES)
    err = (
        f'Unsupported language "{options.language}"\n'
        f'Only {supp} are supported.\n'
    )
    return Result(None, err, 0)


def parse(
    grammar: str,
    text: str,
    grammar_path: str = '<string>',
    path: str = '<string>',
    externs: Externs = None,
    memoize: bool = False,
) -> Result:
    """Match an input text against the specified grammar.

    This will parse the specified `grammar` and create an interpreter for it,
    and then run the interpreter to parse the provided `text`.
    `grammar_path` can be provided to indicate the file path for the given
    grammar, and `path` can be provided to indicate the file path for the
    text; both will be used in error messages. If `memoize` is True, then
    the parser will cache intermediate results during the parse; this may
    provide significant speedups for some grammars, but probably isn't
    helpful for most of them.

    The returned `Result` object has three members: a `val` member containing
    the results of a successful parse, a `err` member containing any errors
    that occur when parsing the grammar or the text, and a `pos` member.
    If the parse is successful, `pos` will point to the position in the
    string where the parser stopped. If there is an error, `pos` will
    indicate where in the string the error occurred.
    """
    result = compile(grammar, grammar_path, memoize=memoize)
    if result.err:
        return Result(err='Error in grammar: ' + result.err, pos=result.pos)
    assert result.parser is not None
    return result.parser.parse(text, path, externs)


def pretty_print(
    grammar: str,
    path: str = '<string>',
    externs=None,
    rewrite_filler: bool = False,
    rewrite_subrules: bool = False,
) -> Tuple[Optional[str], Optional[str]]:
    """Pretty-print a grammar.

    `grammar` is the grammar to parse and format. `path` can be used to
    indicate the path to a file containing the grammar. If there are errors
    in the grammar, `path` will be included in any error messages.

    Returns a tuple of two results. The first is the formatted string, if
    the formatting was successful. The second will be a string describing
    any errors, if it wasn't. If one of the values in the tuple is non-None,
    the other will be None.

    If `rewrite_filler` is true, then the grammar will be printed with
    the filler nodes inserted into it as appropriate. This can be used
    to translate a grammar with filler to a grammar without filler.

    If `rewrite_subrules` is true, then any complex subrules will be
    extracted out into their own rules. You probably normally don't want
    this, but it might be useful to debug something.
    """
    result = parser.parse(grammar, path)
    if result.err:
        return None, result.err

    externs = externs or {}
    try:
        g = analyzer.analyze(
            result.val,
            rewrite_filler=rewrite_filler,
            rewrite_subrules=rewrite_subrules,
        )
        return Printer(g).dumps(), None
    except analyzer.AnalysisError as e:
        return None, str(e)


def dump_ast(
    grammar: str,
    path: str = '<string>',
    rewrite_filler: bool = False,
    rewrite_subrules: bool = False,
) -> Tuple[Optional[str], Optional[str]]:
    """Returns the parsed AST from the grammar. Possibly useful for debugging.

    `rewrite_filler` and `rewrite_subrules` work as in the other methods.
    """
    result = parser.parse(grammar, path)
    if result.err:
        return None, result.err

    try:
        g = analyzer.analyze(
            result.val,
            rewrite_filler=rewrite_filler,
            rewrite_subrules=rewrite_subrules,
        )
        return g.ast, None
    except analyzer.AnalysisError as e:
        return None, str(e)
