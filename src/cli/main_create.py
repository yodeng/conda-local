#!/usr/bin/env python
# coding:utf-8

from ..src import *


def configure_parser(sub_parsers):
    help_desc = "Create a new conda environment from a list of specified packages."
    example = dedent("""
        Examples:
        
            conda local create -n myenv pysam
        """)
    p = sub_parsers.add_parser(
        'create',
        help=help_desc,
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
    p.add_argument(
        '--ignore-pip',
        help="Do not install pip package.",
        action='store_true',
        default=False,
    )
    add_parser_local_solver(p)
    add_parse_no_default_channels(p)
    add_parser_spec(p)
    add_parser_prefix(p)
    p.set_defaults(func='.cli.main_create.execute')


def execute(args):
    prefix = determine_target_prefix(context, args)
    lc = LocalConda(prefix, args)
    lc.create()
