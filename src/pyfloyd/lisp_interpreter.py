# Copyright 2025 Dirk Pranke. All rights reserved.
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


from collections.abc import Callable, Sequence
from typing import Any, Optional, Union


class InterpreterError(Exception):
    pass


def check(flag: bool, msg: str = ''):
    """Check a condition and raise a lisp.InterpreterError if false

    This is like the assert statement, but it raises an InterpreterError
    instead of an AssertionError.
    """
    if not flag:
        raise InterpreterError(msg)


def is_atom(el: Any) -> bool:
    return isinstance(el, (bool, int, float, str)) or el is None


def is_bool(el: Any) -> bool:
    return isinstance(el, bool)


def is_dict(el: Any) -> bool:
    return isinstance(el, dict)


def is_fn(el: Any) -> bool:
    return isinstance(el, Fn)


def is_foreign(el: Any, env: 'Env') -> bool:
    del env
    return not (is_atom(el) or is_list(el) or is_dict(el) or is_fn(el))


def is_list(el: Any) -> bool:
    return isinstance(el, Sequence)


def is_null(el: Any) -> bool:
    return el is None


def is_number(el: Any) -> bool:
    return isinstance(el, (int, float))


def is_str(el: Any) -> bool:
    return isinstance(el, str)


def is_symbol(el: Any) -> bool:
    return is_list(el) and len(el) == 2 and el[0] == 'symbol' and is_str(el[1])


def symbol(el: Any) -> str:
    check(is_symbol(el), f"{el} isn't a symbol")
    return el[1]


CheckerType = Union[str, tuple[Callable[[Any], bool]]]

_typecheckers: dict[str, tuple[Callable[[Any], bool], str]] = {
    'any': (lambda x: True, 'any'),
    'bool': (is_bool, 'bool'),
    'dict': (is_dict, 'dict'),
    'fn': (is_fn, 'function'),
    'list': (is_list, 'list'),
    'num': (is_number, 'number'),
    'str': (is_str, 'string'),
    'sym': (is_symbol, 'symbol'),
}


def typecheck(name: str, types: list[CheckerType], args: list[Any]):
    check(
        len(types) == len(args),
        (
            f'Wrong number of arguments passed to `{name}`: '
            f'expected {len(types)}, got {len(args)}'
        ),
    )
    for i, ty in enumerate(types):
        if isinstance(ty, str):
            ty_fn, ty_name = _typecheckers[ty]
        else:
            assert isinstance(ty, list) and len(ty) == 2
            ty_fn, ty_name = ty
        if ty_name != 'any':
            check(
                ty_fn(args[i]),
                (
                    f'{name} arg #{i} ({repr(args[i])}) passed to `{name}`'
                    f'is not a {ty_name}'
                ),
            )


class Env:
    def __init__(
        self,
        *,
        parent: Optional['Env'] = None,
        values: Optional[dict[str, Any]] = None,
    ):
        self.parent = parent
        self.values = values or {}

    def __repr__(self):
        inner = sorted(self.values.keys())
        outer = self.parent.keys() if self.parent else []
        return f'Env<inner={repr(inner)}, outer={repr(outer)}>'

    def keys(self) -> list[str]:
        ks = list(self.values.keys())
        if self.parent:
            ks.extend(self.parent.keys())
        return sorted(set(ks))

    def bound(self, key: str) -> bool:
        if '.' in key:
            symbols = key.split('.')
            if not self.bound(symbols[0]):
                return False
            v = self.get(symbols[0])
            for sym in symbols[1:]:
                if not hasattr(v, sym):
                    return False
                v = getattr(v, sym)
            return True

        if key in self.values:
            return True
        if self.parent:
            return self.parent.bound(key)
        return False

    def get(self, key: str) -> Any:
        check(self.bound(key), f"Unbound symbol '{key}'")
        if '.' in key:
            symbols = key.split('.')
            v = self.get(symbols[0])
            for sym in symbols[1:]:
                v = getattr(v, sym)
            return v
        if key in self.values:
            return self.values[key]
        assert self.parent is not None
        return self.parent.get(key)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value


EvalFn = Callable[[list[Any], Env], Any]


class Fn:
    def __init__(
        self,
        interp: 'Interpreter',
        env: Env,
        is_fexpr: bool,
        name: str,
        types: Optional[list[CheckerType]],
    ):
        self.interp = interp
        self.env = env or self.interp.env
        self.is_fexpr = is_fexpr
        self.name = name
        self.types = types

    def call(self, args, env):
        raise NotImplementedError


class NativeFn(Fn):
    def __init__(
        self,
        interp: 'Interpreter',
        func: EvalFn,
        env: Optional[Env] = None,
        is_fexpr: bool = True,
        name: str = '<native fn>',
        types: Optional[list[CheckerType]] = None,
    ):
        env = env or interp.global_env
        super().__init__(interp, env, is_fexpr, name, types)
        self.func = func

    def call(self, args, env):
        if self.types and not self.is_fexpr:
            typecheck(self.name, self.types, args)
        return self.func(args, env)


class UserFn(Fn):
    def __init__(
        self,
        interp: 'Interpreter',
        params: list[str],
        body: Any,
        env: Optional[Env] = None,
        is_fexpr: bool = True,
        name: str = '<user fn>',
        types: Optional[list[CheckerType]] = None,
    ):
        env = env or interp.global_env
        super().__init__(interp, env, is_fexpr, name, types)
        self.params: list[str] = []
        for param in params:
            check(is_str(param))
            self.params.append(param)
        self.body = body

    def call(self, args: list[Any], env: Env):
        if self.types:
            typecheck(self.name, self.types, args)
        new_env = Env(values=dict(zip(self.params, args)), parent=self.env)
        return self.interp.eval(self.body, new_env)


class Interpreter:
    def __init__(self):
        self.env = Env()
        self.global_env = self.env
        self.foreign_handlers = []

        self.env.set('true', True)
        self.env.set('false', False)
        self.env.set('null', None)
        self.define_native_fn('define', self.fexpr_define, is_fexpr=True)
        self.define_native_fn('equal', self.f_equal, types=['any', 'any'])
        self.define_native_fn('if', self.fexpr_if, is_fexpr=True)
        self.define_native_fn('in', self.f_in, types=['any', 'any'])
        self.define_native_fn('is_empty', self.f_is_empty)
        self.define_native_fn('fn', self.fexpr_fn, is_fexpr=True)
        self.define_native_fn('getattr', self.f_getattr, types=['any', 'any'])
        self.define_native_fn('getitem', self.f_getitem, types=['any', 'any'])
        self.define_native_fn('join', self.f_join, types=['str', 'list'])
        self.define_native_fn('keys', self.f_keys)
        self.define_native_fn('list', self.f_list)
        self.define_native_fn('map', self.f_map)
        self.define_native_fn('map_items', self.f_map_items)
        self.define_native_fn('quote', self.fexpr_quote, is_fexpr=True)
        self.define_native_fn(
            'replace', self.f_replace, types=['str', 'str', 'str']
        )
        self.define_native_fn('to_string', self.f_to_string, types=['num'])
        self.define_native_fn(
            'slice', self.f_slice, types=['list', 'num', 'num']
        )
        self.define_native_fn('sort', self.f_sort, types=['list'])
        self.define_native_fn('strcat', self.f_strcat)
        self.define_native_fn('strlen', self.f_strlen, types=['str'])

    def add_foreign_handler(self, func: Any):
        self.foreign_handlers.append(func)

    def define_native_fn(
        self,
        name: str,
        func: EvalFn,
        is_fexpr: bool = False,
        types: Optional[list[CheckerType]] = None,
    ) -> None:
        fn = NativeFn(self, func, self.global_env, is_fexpr, name, types)
        self.env.set(name, fn)

    def define(self, name: str, expr: Any) -> None:
        self.env.set(name, self.eval(expr))

    def eval(self, expr: Any, env: Optional[Env] = None) -> Any:
        env = env or self.env
        if is_atom(expr) or is_dict(expr):
            return expr
        if is_symbol(expr):
            sym = symbol(expr)
            check(env.bound(sym), f"Unbound symbol '{sym}'")
            return env.get(sym)
        if is_list(expr):
            first = expr[0]
            rest = expr[1:]
            fn = self.eval(first, env)
            check(is_fn(fn), f"Don't know how to apply `{fn}`")
            if fn.is_fexpr:
                # Don't evaluate the args when calling an fexpr.
                return fn.call(rest, env)
            args = []
            for r in rest:
                args.append(self.eval(r, env))
            return fn.call(args, env)
        for handler in self.foreign_handlers:
            handled, val = handler(expr, env)
            if handled:
                return val
        raise InterpreterError("Don't know how to evaluate `{expr}`")

    def fexpr_define(self, args, env):
        head, body = args
        name = self.eval(head, env)
        self.env.set(name, self.eval(body, env))

    def f_equal(self, args, env):
        del env
        return args[0] == args[1]

    def f_getattr(self, args, env):
        del env
        return getattr(args[0], args[1])

    def f_getitem(self, args, env):
        del env
        return args[0][args[1]]

    def f_in(self, args, env):
        del env
        key, d = args
        return key in d

    def f_is_empty(self, args, env):
        del env
        check(is_list(args[0]) or is_dict(args[0]))
        return len(args[0]) == 0

    def f_join(self, args, env):
        del env
        sep = args[0]
        rest = args[1]
        return sep.join(rest)

    def f_keys(self, args, env):
        del env
        return list(args[0].keys())

    def f_map(self, args, env):
        if len(args) == 3:
            fn, exprs, sep = args
            check(is_str(sep), f"Third arg to map isn't a string: `{sep}`")
        else:
            fn, exprs = args
            sep = None
        check(is_fn(fn), f"First arg to map isn't a function: `{fn}`")
        check(is_list([exprs]), f"Second arg to map isn't a list: `{exprs}`")
        results = []
        for expr in exprs:
            results.append(fn.call([expr], env))
        if sep is not None:
            for i, result in enumerate(results):
                check(
                    is_str(result),
                    f'Arg #{i} to map is not a string: {repr(result)}',
                )
            return sep.join(results)
        return results

    def f_map_items(self, args, env):
        if len(args) == 3:
            fn, d, sep = args
            check(
                is_str(sep), f"Third arg to map_items isn't a string: `{sep}`"
            )
        else:
            fn, d = args
            sep = None
        check(is_fn(fn), f"First arg to map_items isn't a function: `{fn}`")
        check(is_dict(d), f"Second arg to map_items isn't a dict: `{fn}`")
        results = []
        for k, v in d.items():
            results.append(fn.call([k, v], env))
        if sep is not None:
            for i, result in enumerate(results):
                check(
                    is_str(result),
                    f'Arg #{i} to map_items is not a string: {repr(result)}',
                )
            return sep.join(results)
        return results

    def f_list(self, args, env):
        del env
        return list(args)

    def f_replace(self, args, env):
        del env
        s, old, new = args
        return s.replace(old, new)

    def f_slice(self, args, env):
        del env
        lis, start, stop = args
        return lis[start:stop]

    def f_sort(self, args, env):
        del env
        return sorted(args[0])

    def f_strcat(self, args, env):
        del env
        return ''.join(args)

    def f_strlen(self, args, env):
        del env
        return len(args[0])

    def f_to_string(self, args, env):
        del env
        return f'{args[0]}'

    def fexpr_fn(self, args, env):
        param_symbols, body = args
        names = []
        for expr in param_symbols:
            names.append(symbol(expr))
        return UserFn(self, names, body, env, is_fexpr=False)

    def fexpr_if(self, args, env):
        cond, t_expr, f_expr = args
        res = self.eval(cond, env)
        if res:
            return self.eval(t_expr, env)
        return self.eval(f_expr, env)

    def fexpr_quote(self, args, env):
        del env
        # The difference from `f_list`, above, is that the args will
        # not have been evaluated here.
        return args[0]
