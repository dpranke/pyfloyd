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

"""A Parser generator and interpreter framework for Python."""

import argparse
import sys

from floyd.host import Host
from floyd.version import __version__


class _Bailout(Exception):
    pass


def main(argv=None, host=None):
    host = host or Host()

    parser = argparse.ArgumentParser(prog='floyd', description=__doc__)
    parser.add_argument(
        '-V',
        '--version',
        action='store_true',
        help='print floyd version number',
    )
    args = parser.parse_args(argv)

    if args.version:
        host.print(__version__)
        return 0

    return 0


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
