#!/usr/bin/env python
# coding:utf-8

from ..src import *


def configure_parser(sub_parsers):
    description = "Create a new conda environment from a list of specified packages."
    example = dedent("""
        Examples:
        
            conda local create -n myenv pysam
        """)
    p = sub_parsers.add_parser(
        'create',
        description=description,
        help=description,
        epilog=example,
    )
    p.add_argument(
        '-c', '--channel',
        dest='channel',
        action="append",
        help="channel to search package",
    )
    p.add_argument(
        '-q', "--quiet",
        action='store_true',
        default=NULL,
        help="Do not display progress bar.",
    )
    p.add_argument(
        "-y", "--yes",
        action="store_true",
        default=NULL,
        help="Do not ask for confirmation.",
    )
    p.add_argument(
        '--dry-run',
        help=('dry run'),
        action='store_true',
        default=False,
    )
    add_parse_no_default_channels(p)
    p.add_argument(
        'packages',
        metavar='package_spec',
        action="store",
        nargs='*',
        help="Packages to install or update in the conda environment.",
    )
    add_parser_prefix(p)
    p.set_defaults(func='.cli.main_create.execute')


def execute(args):
    prefix = determine_target_prefix(context, args)
    lc = LocalConda(prefix, args)
    lc.create()
