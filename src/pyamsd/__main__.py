import sys
import pathlib
import contextlib

from clldutils.clilib import get_parser_and_subparsers, register_subcommands, PathType
from clldutils.loglib import Logging

import pyamsd.commands
from pyamsd.api import Amsd


def main(args=None, catch_all=False, parsed_args=None):
    parser, subparsers = get_parser_and_subparsers('asjp')
    parser.add_argument(
        '--repos',
        help="path to amsd-data repository",
        type=PathType(type='dir'),
        default=pathlib.Path(
            __file__).resolve().parent.parent.parent.parent.parent / 'amsd' / 'amsd-data')
    register_subcommands(subparsers, pyamsd.commands)

    args = parsed_args or parser.parse_args(args=args)

    if not hasattr(args, "main"):  # pragma: no cover
        parser.print_help()
        return 1

    args.api = Amsd(args.repos)
    with contextlib.ExitStack() as stack:
        stack.enter_context(Logging(args.log, level=args.log_level))
        try:
            return args.main(args) or 0
        except KeyboardInterrupt:  # pragma: no cover
            return 0
        except Exception as e:  # pragma: no cover
            if catch_all:
                print(e)
                return 1
            raise


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main() or 0)
