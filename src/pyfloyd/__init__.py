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

"""A parsing framework and parser generator for Python.

This package can be used to parse texts according to a given grammar
and to generate modules that can be used to parse texts.

The grammars in question are a form of Parsing Expression Grammar.
The grammars support left recursion and can be used to specify operator
precedence in expressions as well. The parse results are in the form
of JSON objects (or their Python equivalents, anyway).

Given a grammar:

    >>> grammar = \"\"\"
    grammar = hello ' '* world { $1 + ', ' $3] }
    hello   = 'Hello'
    world   = 'world'
    \"\"\"

And the input text 'Hello world', the parser will return the string
'Hello, world'.

You can call the `parse` function to do this most easily:

    >>> result = pyfloyd.parse(grammar, 'Hello world')
    >>> result.val
    'Hello, world'
    >>>

Following the `re` module, you can also call a `compile` function to
compile the parser ahead of time:

    >>> parser, _, _ = pyfloyd.compile(grammar)
    >>> result = parse.parse('Hello world')
    Result(val='Hello, world', err=None, pos=11)
    >>>
"""

from types import ModuleType


from pyfloyd.api import (  # noqa: F401 (unused-import)
    add_generator_arguments,
    compile_to_parser,
    dump_ast,
    parse,
    generate,
    generator_options_from_args,
    pretty_print,
    CompiledResult,
    Externs,
    GeneratorOptions,
    Grammar,
    ParserInterface,
    Result,
    DEFAULT_GENERATOR,
    DEFAULT_LANGUAGE,
    DEFAULT_TEMPLATE,
    KNOWN_LANGUAGES,
    KNOWN_TEMPLATES,
    __version__,
)


__all__ = []
for _k in list(globals()):
    if not isinstance(globals()[_k], ModuleType):
        __all__.append(_k)
