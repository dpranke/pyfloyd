# Copyright 2025 Google Inc. All rights reserved.
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

from pyfloyd import (
    at_exp_parser,
    formatter,
    lisp_interpreter,
    string_literal,
)


def bind_at_exps(interp, indent, use_format_objs=True):
    AtExprHandler(interp, indent, use_format_objs)


class AtExprHandler:
    def __init__(
        self,
        interp: lisp_interpreter.Interpreter,
        indent: str,
        use_format_objs: bool,
    ):
        self.interp = interp
        self.indent = indent
        self.use_format_objs = use_format_objs
        interp.define_native_fn('at_exp', self.f_at_exp, types=['str'])
        interp.define_native_fn('comma', self.f_comma)
        interp.define_native_fn('hang', self.f_hang)
        interp.define_native_fn('hl', self.f_hl)
        interp.define_native_fn('ind', self.f_ind)
        interp.define_native_fn('lit', self.f_lit)
        interp.define_native_fn('saw', self.f_saw)
        interp.define_native_fn('tree', self.f_tree)
        interp.define_native_fn('tri', self.f_tri)
        interp.define_native_fn('vl', self.f_vl)
        interp.define_native_fn('wrap', self.f_wrap)
        interp.add_foreign_handler(self._eval_format_obj)

    def _eval_format_obj(
        self, expr: Any, env: lisp_interpreter.Env
    ) -> tuple[bool, Any]:
        del env
        if isinstance(expr, formatter.FormatObj):
            return True, expr
        return False, None

    def f_at_exp(self, args, env) -> Any:
        exprs, err, _ = at_exp_parser.parse(args[0], '-')
        lisp_interpreter.check(
            err is None, f'Unexpected at_exp parse error: {err}'
        )
        values = [self.interp.eval(expr, env) for expr in exprs]

        if self.use_format_objs:
            return process_values(values, self.indent)
        return values

    def f_comma(self, args, env) -> Any:
        del env
        return formatter.Comma(*args[0])

    def f_hang(self, args, env) -> Any:
        del env
        return formatter.Hang(*args, indent=self.indent)

    def f_hl(self, args, env) -> Any:
        del env
        return formatter.HList(args)

    def f_ind(self, args, env) -> Any:
        del env
        return formatter.Indent(args, indent=self.indent)

    def f_lit(self, args, env) -> Any:
        del env
        s = args[0]
        return string_literal.encode(s)

    def f_saw(self, args, env) -> Any:
        del env
        return formatter.Saw(*args[0])

    def f_tree(self, args, env) -> Any:
        del env
        return formatter.Tree(*args)

    def f_tri(self, args, env) -> Any:
        del env
        return formatter.Triangle(*args)

    def f_vl(self, args, env) -> Any:
        del env
        return formatter.VList(args, indent=self.indent)

    def f_wrap(self, args, env) -> Any:
        del env
        return formatter.Wrap(*args, indent=self.indent)


def process_values(values, indent):
    results = []

    # If the only thing on the line was a newline, keep it.
    if values == ['\n']:
        return formatter.VList('')

    # Iterate through the list of objects returned from evaluating the
    # at-exp string. Whenever we hit a newline, look at the values since
    # the last newline and decide what to do with them.
    current_values = []
    for v in values:
        if v == '\n':
            results.extend(_process_one_line_of_values(current_values, indent))
            current_values = []
        else:
            current_values.append(v)

    # Also process any arguments following the last newline (or, all
    # of the arguments, if there was no newline).
    if len(current_values) != 0:
        results.extend(_process_one_line_of_values(current_values, indent))
    vl = formatter.VList(results)
    return vl


def _process_one_line_of_values(values, indent):
    # Drop the line if appropriate (see below). This allows embedded
    # at-exps and functions to avoid trailing newlines and unwanted
    # blank lines resulting in the output.
    if _should_drop_the_line(values):
        return []

    # If there is just one value on the line and it is a FormatObj, return it.
    if len(values) == 1 and isinstance(values[0], formatter.FormatObj):
        return [values[0]]

    if len(values) == 1 and isinstance(values[0], str):
        if values[0].startswith(' ') or '\n' in values[0]:
            return [formatter.split_to_objs(values[0], indent)]
        return [values[0]]

    # If the set is a series of spaces followed by a FormatObj,
    # indent and return the format obj.
    if (
        len(values) == 2
        and isinstance(values[0], str)
        and values[0].isspace()
        and isinstance(values[1], formatter.VList)
    ):
        level = formatter.indent_level(values[0], indent)
        obj = values[1]
        while level > 0:
            obj = formatter.Indent(obj)
            level -= 1
        return [obj]

    # If everything is a string or an HList, return an HList containing them.
    use_hl = True
    for v in values:
        if not isinstance(v, (str, formatter.HList)):
            use_hl = False
            break
        if isinstance(v, str) and '\n' in v:
            use_hl = False
            break
    if use_hl:
        return [formatter.HList(*values)]
    assert False, f'unexpected line of values: {repr(values)}'


# A line of values should be dropped (or skipped) when:
# - At least one value is either None or a VList with no elements.
# - Any other values are whitespace.
def _should_drop_the_line(values):
    has_empty_value = False
    has_non_empty_string = False
    for v in values:
        if v is None:
            has_empty_value = True
        if isinstance(v, formatter.VList) and v.is_empty():
            has_empty_value = True
        if isinstance(v, str) and not v.isspace():
            has_non_empty_string = True
    return has_empty_value and not has_non_empty_string
