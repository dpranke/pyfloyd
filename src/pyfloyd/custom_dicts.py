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

from typing import Any


class AttrDict(dict):
    """A very simple subclass of dict that permits direct reference to keys.

    If a dict d contains the key 'foo', then you can access it with
    `d.foo` as well as `d['foo']`."""

    def __getattr__(self, name):
        return self.__getitem__(name)

    def __setattr__(self, name, value):
        return self.__setitem__(name, value)

    def update(self, *args, **values):
        for k, v in dict(*args, **values).items():
            self[k] = v


class FixedDict(dict):
    """A custom subclass of `dict` with a fixed set of keys().

    Subclasses must override the `_keys` field to list the keys they support.

    This class exists to provide objects that have a more strongly typed
    interface than a regular `dict`. It subclasses dict directly rather
    than implementing `collections.abc.MutableMapping` in order to work
    transparently with the standard JSON marsalling routines (dump/dumps),
    which only handle actual dicts by default unless a custom decoder is
    provided (See also https://github.com/python/cpython/issues/110941,
    which requires us to use the underlying dict's storage for this
    rather than regular slots).

    Likely the *only* good reason to use this class instead of something
    like a NamedTuple, a dataclass, or an ABC is for the class to
    work w/ JSON.dump by default.

    The fixed set of keys can be referred to directly by attribute in
    addition to being dereferenced via getitem/setitem.

    These objects are not interchangeable with dicts, a given object is only
    equal to another object of the same type, and only a subset of the dict
    interface is supported, as you can't get or set arbitary keys.

    You can get a real dict from the object using `to_dict()`, but that
    returns a *copy* of the object.
    """

    _keys: tuple[str, ...] = ()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and super().__eq__(other)

    def __getattr__(self, key) -> Any:
        if key not in self._keys:
            raise KeyError(f'{self.__class_} does not have a `{key}` key')
        return self.__getitem__(key)

    def __setattr__(self, key, value):
        if key not in self._keys:
            raise KeyError(f'{self.__class_} does not have a `{key}` key')
        self.__setitem__(key, value)

    def __delitem__(self, key):
        raise TypeError(f'{self.__class__} does not support `del`')

    def get(self, key: Any, default: Any = None) -> Any:
        if key not in self:
            raise TypeError(
                f'{self.__class__} does not support get() for arbitrary keys'
            )
        return super().get(key, default)

    def to_dict(self) -> dict[str, Any]:
        """Returns a regular dict that is otherwise a copy of this object."""
        return {
            'base': self.base,
            'elements': [el.to_dict() for el in self.elements],
        }
