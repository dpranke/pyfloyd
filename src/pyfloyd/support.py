# Copyright 2017 Google Inc. All rights reserved.
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

import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


class Host:
    def __init__(self):
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def exists(self, path):
        return os.path.exists(path)

    def make_executable(self, path):
        os.chmod(path, 0o755)

    def mkdtemp(self):
        return tempfile.mkdtemp()

    def print(self, *args, end='\n', file=None, flush=True):
        file = file or self.stdout
        print(*args, end=end, file=file, flush=flush)

    def rmtree(self, path):
        shutil.rmtree(path)

    def splitext(self, path):
        return os.path.splitext(path)

    def read_text_file(self, path):
        with open(path, encoding='utf-8') as f:
            return f.read()

    def write_text_file(self, path, contents):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(contents)


class FakeHost:
    def __init__(self):
        self.stderr = io.StringIO()
        self.stdin = io.StringIO()
        self.stdout = io.StringIO()
        self.files = {}
        self.written_files = {}

    def exists(self, path):
        return path in self.files

    def make_executable(self, path):
        pass

    def print(self, *args, end='\n', file=None):
        file = file or self.stdout
        print(*args, end=end, file=file, flush=True)

    def read_text_file(self, path):
        return self.files[path]

    def splitext(self, path):
        return path.rsplit('.')

    def write_text_file(self, path, contents):
        self.files[path] = contents
        self.written_files[path] = contents
