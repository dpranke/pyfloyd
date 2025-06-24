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

from typing import Any, Optional

from pyfloyd import custom_dicts

BASIC_TYPES = ('any', 'bool', 'float', 'func', 'int', 'null', 'str', 'wip')
COMPOUND_TYPES = ('dict', 'list', 'tuple')


def d2str(d: dict[str, Any]) -> str:
    return TypeDesc.d2str(d)


def str2d(s: str) -> dict[str, Any]:
    return TypeDesc(s).to_dict()


def from_str(s: str) -> 'TypeDesc':
    return TypeDesc(s)


def from_dict(d: dict[str, Any]) -> 'TypeDesc':
    return TypeDesc.from_dict(d)


class TypeDesc(custom_dicts.FixedDict):
    _keys = ('base', 'elements')

    def __init__(self, base: str, elements: Optional[list['TypeDesc']] = None):
        elements = elements or []
        self.base = base
        self.elements = elements
        if '[' in base:
            got = TypeDesc.from_str(base)
            self.base = got.base
            self.elements = got.elements
            return
        if base in BASIC_TYPES:
            assert len(elements) == 0
        elif base in COMPOUND_TYPES:
            if base == 'list':
                if len(elements) != 1:
                    raise ValueError(
                        f'Wrong number of elements ({len(elements)}) in {base} '
                        f'type descriptor'
                    )
            if base == 'dict':
                if len(elements) != 2:
                    raise ValueError(
                        f'Wrong number of elements ({len(elements)}) in {base} '
                        f'type descriptor'
                    )
            for el in elements:
                assert isinstance(el, TypeDesc)
        else:
            # Custom type; ignore it.
            # TODO: is this the right thing to do?
            pass

    def __repr__(self):
        return "TypeDesc('" + self.to_str() + "')"

    def __str__(self):
        return self.to_str()

    def to_str(self) -> str:
        if self.base in BASIC_TYPES:
            return self.base
        el_str = ', '.join(el.to_str() for el in self.elements)
        return self.base + '[' + el_str + ']'

    @staticmethod
    def d2str(d: dict[str, Any]) -> str:
        return TypeDesc.from_dict(d).to_str()

    @staticmethod
    def from_dict(d: dict[str, Any]) -> 'TypeDesc':
        return TypeDesc(
            d['base'], [TypeDesc.from_dict(el) for el in d['elements']]
        )

    @staticmethod
    def from_str(s: str, allow_trailing: bool = False) -> 'TypeDesc':
        for ty in BASIC_TYPES:
            if s.startswith(ty):
                if not allow_trailing and s != ty:
                    _raise(s)
                return TypeDesc(ty)
        if '[' not in s:
            _raise(s)
        pfx, sfx = s.split('[', maxsplit=1)
        if pfx not in COMPOUND_TYPES:
            _raise(s)
        els = []
        sfx = sfx[:-1]
        while sfx:
            if sfx.startswith(']') or sfx == '':
                break
            el = TypeDesc.from_str(sfx, allow_trailing=True)
            els.append(el)
            rs = el.to_str()
            sfx = sfx[len(rs) :]
            if sfx.startswith(', '):
                sfx = sfx[2:]
                continue
            if sfx != '' and not sfx.startswith(']'):
                _raise(s)
        if not allow_trailing and sfx != '':
            _raise(s)
        if pfx == 'list':
            if len(els) != 1:
                _raise(s)
        if pfx == 'dict':
            if len(els) != 2 or els[0] != TypeDesc('str'):
                _raise(s)

        return TypeDesc(pfx, els)


def check(exp: str, got: str):
    return check_descs(TypeDesc.from_str(exp), TypeDesc.from_str(got))


def check_descs(exp: TypeDesc, got: TypeDesc):
    if got == exp:
        return True
    if exp.base == 'any':
        return True
    if exp.base == 'list' and got.base == 'tuple':
        return all(check_descs(exp.elements[0], el) for el in got.elements)
    if exp.base != got.base:
        return False
    if len(exp.elements) != len(got.elements):
        return False
    return all(
        check_descs(exp.elements[i], got.elements[i])
        for i in range(len(exp.elements))
    )


def merge(types: list[str]) -> str:
    if len(types) == 1:
        return types[0]
    list_ty = None
    for ty in types:
        if 'list' in ty:
            list_ty = ty

    if list_ty:
        list_td = TypeDesc.from_str(list_ty)
        for ty in types:
            if ty == list_ty:
                continue
            td = TypeDesc.from_str(ty)
            if not check_descs(list_td, td):
                return 'any'
        return list_ty
    return 'any'


def _raise(s: str):
    raise ValueError('Bad type descriptor: ' + s)
