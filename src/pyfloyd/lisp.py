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
from typing import Any, Optional


class Error(Exception):
    pass


def check(val: Any, msg: str = ''):
    if not bool(val):
        raise Error(msg)


def is_atom(el: Any, *, env=None) -> bool:
    del env
    return isinstance(el, (bool, int, float, str))


def is_bool(el: Any, *, env=None) -> bool:
    del env
    return isinstance(el, bool)


def is_callable(el: Any, *, env=None) -> bool:
    del env
    return is_fn(el) or callable(el)


def is_dict(el: Any, *, env=None) -> bool:
    del env
    return isinstance(el, dict)


def is_fn(el: Any, *, env=None) -> bool:
    del env
    return isinstance(el, Fn)


def is_list(el, env=None) -> bool:
    del env
    return isinstance(el, Sequence)


def is_str(el: Any, *, env=None) -> bool:
    del env
    return isinstance(el, str)


def is_symbol(el: Any, *, env=None) -> bool:
    del env
    return is_list(el) and len(el) == 2 and el[0] == 'symbol' and is_str(el[1])


def length(el: Any, *, env=None) -> int:
    del env
    check(is_list(el))
    return len(el)


def symbol(el: Any, *, env=None) -> str:
    del env
    check(is_symbol(el))
    return el[1]


def typecheck(
    name, types: list[tuple[Callable[[Any], bool], str]], args: list[Any]
):
    check(
        len(types) == len(args),
        (
            f'Wrong number of arguments passed to `{name}`: '
            f'expected {len(types)}, got {len(args)}'
        ),
    )
    for i, ty in enumerate(types):
        ty_fn, ty_name = ty
        check(
            ty_fn(args[i]),
            (
                f'f{name} arg #{i} ({repr(args[i])}) passed to `{name}`'
                f'is not a {ty_name}'
            ),
        )


TY_STR = [is_str, 'string']


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
        return f'Env(parent={repr(self.parent)}, values={repr(self.values)})'

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
        if '.' in key:
            symbols = key.split('.')
            v = self.get(symbols[0])
            for sym in symbols[1:]:
                v = getattr(v, sym)
            return v
        if key in self.values:
            return self.values[key]
        assert self.parent
        return self.parent.get(key)

    def set(self, key: str, value: Any):
        self.values[key] = value

    def update(self, d: dict):
        self.values.update(d)


class Fn:
    def __init__(self, interp, parms, body, env):
        self.interp = interp
        self.parms = []
        for parm in parms:
            check(is_symbol(parm))
            self.parms.append(symbol(parm))
        self.body = body
        self.env = env

    def __call__(self, *args):
        env = Env(values=dict(zip(self.parms, args)), parent=self.env)
        return self.interp.eval(self.body, env)


EvalFn = Callable[..., Any]


class Interpreter:
    def __init__(
        self,
        values: Optional[dict[str, Any]] = None,
        fexprs: Optional[dict[str, Any]] = None,
        is_foreign: Optional[EvalFn] = None,
        eval_foreign: Optional[EvalFn] = None,
    ):
        self.env = Env(
            values={
                'map': self.f_map,
                'list': self.f_list,
                'strcat': self.f_strcat,
            }
        )
        self.fexprs: dict[str, EvalFn] = {
            'fn': self.fexpr_fn,
            'if': self.fexpr_if,
        }
        self.is_foreign = is_foreign
        self.eval_foreign = eval_foreign
        if values:
            self.env.update(values)
        if fexprs:
            self.fexprs.update(fexprs)

    def bound(self, key: str) -> bool:
        return self.env.bound(key)

    def get(self, key: str, env: Optional[Env] = None) -> Any:
        env = env or self.env
        return env.get(key)

    def eval(self, expr: Any, env: Optional[Env] = None) -> Any:
        env = env or self.env
        if is_atom(expr) or is_dict(expr):
            return expr
        if self.is_foreign and self.is_foreign(expr, env):
            assert self.eval_foreign is not None
            return self.eval_foreign(expr, env)
        if is_symbol(expr):
            sym = symbol(expr)
            if env.bound(sym):
                return env.get(sym)
            raise Error(f'Unbound symbol "{sym}"')
        check(is_list(expr))
        first = expr[0]
        rest = expr[1:]
        if is_symbol(first):
            sym = symbol(first)
            if sym in self.fexprs:
                return self.fexprs[sym](*rest, env=env)
        v = self.eval(first, env)
        if callable(v):
            args = [self.eval(expr, env) for expr in rest]
            return v(*args)
        raise Error(f"Don't know how to evaluate `{expr}`")

    def fexpr_if(self, cond, t_expr, f_expr, *, env):
        res = self.eval(cond, env)
        if res:
            return self.eval(t_expr, env)
        return self.eval(f_expr, env)

    def fexpr_fn(self, params, body, *, env):
        return Fn(self, params, body, env)

    def f_map(self, fn, exprs, sep=None):
        check(is_list, exprs)
        assert callable(fn)
        if is_dict(exprs):
            result = [fn(k, self.eval(v)) for k, v in exprs.items()]
        else:
            result = [fn(expr) for expr in exprs]
        if sep is not None:
            return sep.join(result)
        return result

    def f_list(self, *rest):
        return list(rest)

    def f_strcat(self, first, second):
        return first + second
