#!/usr/bin/env python
# coding:utf-8

from .src import *


def configure_parser(sub_parsers):
    description = "Installs a list of packages into a specified conda environment from local conda repodata."
    example = dedent("""
        Examples:
        
            conda local install -n myenv pysam
        """)
    p = sub_parsers.add_parser(
        'install',
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
        "-f", '--force-reinstall',
        help=('Force creation of environment (removing a previously-existing '
              'environment of the same name).'),
        action='store_true',
        default=False,
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
    p.add_argument(
        'packages',
        metavar='package_spec',
        action="store",
        nargs='*',
        help="Packages to install in the conda environment.",
    )
    add_parser_prefix(p)
    p.set_defaults(func='.main_install.execute')


def execute(args):
    prefix = determine_target_prefix(context, args)
    lc = LocalConda(prefix, args)
    lc.install()
