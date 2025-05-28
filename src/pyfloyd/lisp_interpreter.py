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
    return isinstance(el, _Fn)


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


class _Fn:
    def __init__(
        self, name: str, types: Optional[list[CheckerType]], is_fexpr: bool
    ):
        self.name = name
        self.types = types
        self.is_fexpr = is_fexpr

    def call(self, args, env):
        raise NotImplementedError


class SimpleFn(_Fn):
    def __init__(
        self,
        func: Callable[[list[Any]], Any],
        name: str,
        types: Optional[list[CheckerType]] = None,
    ):
        super().__init__(name, types, is_fexpr=False)
        self.func = func

    def call(self, args, env):
        del env
        if self.types:
            typecheck(self.name, self.types, args)
        return self.func(args)


class NativeFn(_Fn):
    def __init__(
        self,
        interp: 'Interpreter',
        func: EvalFn,
        name: str = '<native fn>',
        types: Optional[list[CheckerType]] = None,
        env: Optional[Env] = None,
        is_fexpr: bool = False,
    ):
        env = env or interp.global_env
        super().__init__(name, types, is_fexpr)
        self.env = env
        self.interp = interp
        self.func = func

    def call(self, args, env):
        if self.types and not self.is_fexpr:
            typecheck(self.name, self.types, args)
        return self.func(args, env)


class UserFn(_Fn):
    def __init__(
        self,
        interp: 'Interpreter',
        params: Union[str, list[str]],
        body: Any,
        env: Optional[Env] = None,
        is_fexpr: bool = False,
        name: str = '<user fn>',
        types: Optional[list[CheckerType]] = None,
    ):
        env = env or interp.global_env
        super().__init__(name, types, is_fexpr)
        self.env = env
        self.interp = interp
        self.is_fexpr = is_fexpr
        self.params = params
        self.body = body

    def call(self, args: list[Any], env: Env):
        if self.types:
            typecheck(self.name, self.types, args)
        if isinstance(self.params, list):
            values = dict(zip(self.params, args))
        else:
            values = {self.params: args}
        new_env = Env(values=values, parent=self.env)
        return self.interp.eval(self.body, new_env)


class Interpreter:
    def __init__(self):
        self.env = Env()
        self.global_env = self.env
        self.foreign_handlers = []

        self.env.set('true', True)
        self.env.set('false', False)
        self.env.set('null', None)
        self.define_native_fn('fn', self.fexpr_fn, is_fexpr=True)
        self.define_native_fn('define', self.fexpr_define, is_fexpr=True)
        self.define_native_fn('if', self.fexpr_if, is_fexpr=True)
        self.define_native_fn('quote', self.fexpr_quote, is_fexpr=True)

        self.define_simple_fn('cons', f_cons, types=['any', 'list'])
        self.define_simple_fn('equal', f_equal, types=['any', 'any'])
        self.define_simple_fn('in', f_in, types=['any', 'any'])
        self.define_simple_fn('is_empty', f_is_empty)
        self.define_simple_fn('getattr', f_getattr, types=['any', 'any'])
        self.define_simple_fn('getitem', f_getitem, types=['any', 'any'])
        self.define_simple_fn('join', f_join, types=['str', 'list'])
        self.define_simple_fn('keys', f_keys, types=['dict'])
        self.define_simple_fn('length', f_length)
        self.define_simple_fn('list', f_list)
        self.define_simple_fn(
            'replace', f_replace, types=['str', 'str', 'str']
        )
        self.define_simple_fn('to_string', f_to_string, types=['any'])
        self.define_simple_fn('slice', f_slice, types=['list', 'num', 'num'])
        self.define_simple_fn('sort', f_sort, types=['list'])
        self.define_simple_fn('strcat', f_strcat)
        self.define_simple_fn('strlen', f_strlen, types=['str'])

        self.define_native_fn('map', self.f_map)
        self.define_native_fn('map_items', self.f_map_items)

    def add_foreign_handler(self, func: Any):
        self.foreign_handlers.append(func)

    def define_simple_fn(
        self,
        name: str,
        func: Callable[[list[Any]], Any],
        types: Optional[list[CheckerType]] = None,
    ) -> None:
        fn = SimpleFn(func, name, types)
        self.env.set(name, fn)

    def define_native_fn(
        self,
        name: str,
        func: EvalFn,
        is_fexpr: bool = False,
        types: Optional[list[CheckerType]] = None,
    ) -> None:
        fn = NativeFn(self, func, name, types, is_fexpr=is_fexpr)
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
        raise InterpreterError(f"Don't know how to evaluate `{expr}`")

    def fexpr_define(self, args, env):
        head, body = args
        name = self.eval(head, env)
        self.env.set(name, self.eval(body, env))

    def fexpr_fn(self, args, env):
        param_symbols, body = args
        if len(param_symbols) and param_symbols[0] == 'symbol':
            params = symbol(param_symbols)
        else:
            params = []
            for expr in param_symbols:
                params.append(symbol(expr))
        if env.bound('_t_name'):
            name = env.get('_t_name')
            if name == '':
                name = None
        return UserFn(self, params, body, env, is_fexpr=False, name=name)

    def fexpr_if(self, args, env):
        cond = args[0]
        t_expr = args[1]
        if len(args) == 3:
            f_expr = args[2]
        else:
            f_expr = ['symbol', 'null']
        res = self.eval(cond, env)
        if res:
            return self.eval(t_expr, env)
        return self.eval(f_expr, env)

    def fexpr_quote(self, args, env):
        del env
        # The difference from `f_list`, above, is that the args will
        # not have been evaluated here.
        return args[0]

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


def f_cons(args):
    hd, tl = args
    return [hd] + tl


def f_equal(args):
    x, y = args
    return x == y


def f_getattr(args):
    obj, attr = args
    return getattr(obj, attr)


def f_getitem(args):
    obj, index = args
    return obj[index]


def f_in(args):
    key, obj = args
    return key in obj


def f_is_empty(args):
    obj = args[0]
    check(is_list(obj) or is_dict(obj))
    return len(obj) == 0


def f_join(args):
    sep, rest = args
    return sep.join(rest)


def f_keys(args):
    d = args[0]
    return list(d.keys())


def f_length(args):
    lis = args[0]
    return len(lis)


def f_list(args):
    return list(args)


def f_replace(args):
    s, old, new = args
    return s.replace(old, new)


def f_slice(args):
    lis, start, stop = args
    return lis[start:stop]


def f_sort(args):
    lis = args[0]
    return sorted(lis)


def f_strcat(args):
    return ''.join(args)


def f_strlen(args):
    s = args[0]
    return len(s)


def f_to_string(args):
    obj = args[0]
    return f'{obj}'
