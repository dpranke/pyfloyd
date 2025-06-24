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

import argparse
import json
import os
import pdb
import sys
import traceback

from pyfloyd import datafile, datafile_generator, generator, support


def main(
    argv=sys.argv[1:],
    stdin=sys.stdin,
    stdout=sys.stdout,
    stderr=sys.stderr,
    exists=os.path.exists,
    opener=open,
) -> int:
    parser = argparse.ArgumentParser()
    generator.add_arguments(parser)
    parser.add_argument('-j', '--json', action='store_true')
    parser.add_argument(
        '-k',
        '--key',
        action='store',
        default='data',
        help='Data will be accessible under this key',
    )
    parser.add_argument(
        '-t',
        '--top-level',
        action='store_const',
        const=None,
        dest='key',
        help='Store data into the top-level environment',
    )

    parser.add_argument(
        '-o',
        '--output',
        action='store',
        default='-',
        help="path to write output to (can use '-' for stdout)",
    )
    parser.add_argument(
        'file',
        nargs='?',
        action='store',
        help="datafile to read for data (can use '-' for stdin))",
    )
    parser.add_argument('--post-mortem', '--pm', action='store_true')
    args = parser.parse_args(argv)

    if not args.file or args.file[1] == '-':
        path = '<stdin>'
        fp = stdin
    elif not exists(args.file):
        print(f'Error: file "{args.file}" not found.', file=stderr)
        return 1
    else:
        path = args.file
        fp = opener(path)

    host = support.Host()
    host.stdin = stdin
    host.stdout = stdout
    host.stderr = stderr
    options = generator.options_from_args(args, sys.argv)

    try:
        if args.json:
            df = json.load(fp)
        else:
            df = datafile.load(fp, filename=path)
        if args.key is None:
            data = df
        else:
            data = {args.key: df}

        dfg = datafile_generator.DatafileGenerator(host, data, options=options)
        s = dfg.generate()

        if args.output == '-':
            print(s, file=stdout, end='')
        else:
            fp = opener(args.output, 'w')
            print(s, file=fp, end='')

    except KeyboardInterrupt:
        host.print('Interrupted, exiting.', file=stderr)
        return 130  # SIGINT
    except datafile.DatafileError as exc:
        if args and args.post_mortem:
            traceback.print_exception(exc)
            pdb.post_mortem()
        print(str(exc), file=host.stderr)
        return 1
    except Exception as exc:  # pylint: disable=broad-exception-caught
        if args and args.post_mortem:
            traceback.print_exception(exc)
            pdb.post_mortem()
        else:
            raise exc
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
