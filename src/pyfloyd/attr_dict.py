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
