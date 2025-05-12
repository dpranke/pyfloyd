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


def check(flag: bool, msg: str = ''):
    if not flag:
        raise Error(msg)


def is_atom(el: Any) -> bool:
    return isinstance(el, (bool, int, float, str))


def is_dict(el: Any) -> bool:
    return isinstance(el, dict)


def is_fn(el: Any) -> bool:
    return isinstance(el, Fn)


def is_list(el: Any) -> bool:
    return isinstance(el, Sequence)


def is_str(el: Any) -> bool:
    return isinstance(el, str)


def is_symbol(el: Any) -> bool:
    return is_list(el) and len(el) == 2 and el[0] == 'symbol' and is_str(el[1])


def symbol(el: Any) -> str:
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

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value

    def update(self, d: dict[str, Any]) -> None:
        self.values.update(d)


class Fn:
    def __init__(
        self,
        interpreter: 'Interpreter',
        params: list[tuple[str, str]],
        body: Any,
        env: Env
    ):
        self.interpreter = interpreter
        self.params = []
        for param in params:
            check(is_symbol(param))
            self.params.append(symbol(param))
        self.body = body
        self.env = env

    def __call__(self, args, env):
        new_env = Env(values=dict(zip(self.params, args)), parent=self.env)
        return self.interpreter.eval(self.body, new_env)


EvalFn = Callable[[list[Any], Env], Any]


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
        self.is_foreign = is_foreign or self._default_is_foreign
        self.eval_foreign = eval_foreign or self._default_is_foreign
        if values:
            self.env.update(values)
        if fexprs:
            self.fexprs.update(fexprs)

    def _default_is_foreign(self, expr: Any, env: Env) -> Any:
        del expr
        del env
        return False

    def _default_eval_foreign(self, expr: Any, env: Env) -> Any:
        raise Error('eval_foreign called by mistake')

    def define(self, name: str, expr: Any) -> None:
        self.env.set(name, self.eval(expr))

    def eval(self, expr: Any, env: Optional[Env] = None) -> Any:
        env = env or self.env
        if is_atom(expr) or is_dict(expr):
            return expr
        if self.is_foreign(expr, env):
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
                return self.fexprs[sym](rest, env)
        v = self.eval(first, env)
        if callable(v):
            args = [self.eval(expr, env) for expr in rest]
            return v(args, env)
        raise Error(f"Don't know how to evaluate `{expr}`")

    def fexpr_if(self, args, env):
        cond, t_expr, f_expr = args
        res = self.eval(cond, env)
        if res:
            return self.eval(t_expr, env)
        return self.eval(f_expr, env)

    def fexpr_fn(self, args, env):
        params, body = args
        return Fn(self, params, body, env)

    def f_map(self, args, env):
        if len(args) == 3:
            fn, exprs, sep = args
        else:
            fn, exprs = args
            sep = '\n'
        check(is_list(exprs) or is_dict(exprs))
        check(callable(fn))
        if is_dict(exprs):
            result = [fn([k, self.eval(v, env)], env) for k, v in exprs.items()]
        else:
            result = [fn([expr], env) for expr in exprs]
        if sep is not None:
            return sep.join(result)
        return result

    def f_list(self, args, env):
        del env
        return list(args)

    def f_strcat(self, args, env):
        del env
        first, second = args
        return first + second
