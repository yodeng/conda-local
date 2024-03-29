#!/usr/bin/env python
# coding:utf-8

from ..src import *


def configure_parser(sub_parsers):
    help_desc = "Download all packages include depency from local conda repodata."
    example = dedent("""
        Examples:
        
            conda local download -c bioconda pysam -o out
        """)
    p = sub_parsers.add_parser(
        'download',
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
        '--dry-run',
        help=('dry run'),
        action='store_true',
        default=False,
    )
    p.add_argument(
        "-y", "--yes",
        action="store_true",
        default=NULL,
        help="Do not ask for confirmation.",
    )
    add_parser_local_solver(p)
    add_parse_no_default_channels(p)
    p.add_argument(
        '-o', '--outdir',
        required=True,
        metavar="<dir>",
        help="directory to save all packages, required",
    )
    add_parser_spec(p)
    p.set_defaults(func='.cli.main_download.execute')


def execute(args):
    lc = LocalConda(None, args)
    lc.download()
