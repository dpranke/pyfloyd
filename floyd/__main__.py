import argparse
import sys

from floyd.version import __version__

if __name__ == '__main__':
    if sys.argv[1] in ('-V', '--version'):
        print(__version__)
        sys.exit(0)
    print('floyd has been renamed to pyfloyd. Run that instead.')
    sys.exit(1)
