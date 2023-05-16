#!/usr/bin/env python
# coding:utf-8

from ..src import *


def configure_parser(sub_parsers):
    description = "Search for packages from local conda repo and display associated information."
    example = dedent("""
        Examples:
            
            conda local search scikit-learn
            conda local search *scikit*
            conda local search '*scikit'
            conda local search "*scikit*"
            conda local search numpy[subdir=linux-64]
            conda local search 'numpy>=1.12'
            conda local search conda-forge::numpy
            conda local search 'numpy[channel=conda-forge, subdir=linux-64]'
        """)
    p = sub_parsers.add_parser(
        'search',
        description=description,
        help=description,
        epilog=example
    )
    p.add_argument(
        '-c', '--channel',
        dest='channel',
        action="append",
        help="channel to search package",
    )
    add_parse_no_default_channels(p)
    p.add_argument(
        '-d', "--detail",
        action="store_true",
        help="Show detailed information about each package."
    )
    p.add_argument(
        'match_spec',
        default='*',
        nargs='?',
        help=SUPPRESS,
    )
    p.set_defaults(func='.cli.main_search.execute')


def execute(args):
    spec = MatchSpec(args.match_spec)
    if spec.get_exact_value('subdir'):
        subdirs = spec.get_exact_value('subdir'),
    else:
        subdirs = context.subdirs
    spec_channel = spec.get_exact_value('channel')
    _channel_urls = (spec_channel,) if spec_channel else context.channels
    local_repo = LocalCondaRepo()
    local_repo.parse_repos()
    channel_urls = LocalConda.file_channels(
        new_channel_names(_channel_urls, args), local_repo)
    local_repo.log.info("Using conda channel: %s", cstring(", ".join(
        flatten([[join(c.base_url if not c.base_url.startswith("file://") else c.base_url[7:], s) for s in context.subdirs] for c in channel_urls])), 0, 34))
    with Spinner("Loading local channels", not context.verbosity and not context.quiet, context.json):
        matches = sorted(SubdirData.query_all(spec, channel_urls, subdirs),
                         key=lambda rec: (rec.name, VersionOrder(rec.version), rec.build))
    if not matches and spec.get_exact_value("name"):
        flex_spec = MatchSpec(spec, name="*%s*" % spec.name)
        if not context.json:
            print("No match found for: %s. Search: %s" % (spec, flex_spec))
        matches = sorted(SubdirData.query_all(flex_spec, channel_urls, subdirs),
                         key=lambda rec: (rec.name, VersionOrder(rec.version), rec.build))
    if not matches:
        channels_urls = tuple(calculate_channel_urls(
            channel_urls=_channel_urls,
            platform=subdirs[0],
        ))
        raise PackagesNotFoundError((str(spec),), channels_urls)
    if args.detail:
        for record in matches:
            pretty_record(record)
    else:
        builder = ['# %-18s %15s %15s  %-20s' % (
            "Name",
            "Version",
            "Build",
            "Channel",
        )]
        for record in matches:
            builder.append('%-20s %15s %15s  %-20s' % (
                record.name,
                record.version,
                record.build,
                record.channel.name,
            ))
        print('\n'.join(builder))
