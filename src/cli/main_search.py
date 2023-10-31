#!/usr/bin/env python
# coding:utf-8

from ..src import *


def configure_parser(sub_parsers):
    help_desc = "Search for packages from local conda repo and display associated information."
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
        help=help_desc,
        epilog=example
    )
    p.add_argument(
        '-c', '--channel',
        dest='channel',
        action="append",
        help="channel to search package",
    )
    add_parser_local_solver(p)
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


def _process_query_result(result_str, records=True):
    if isinstance(result_str, list):
        return sorted(result_str, key=lambda rec: (rec.name, rec.version, rec.build), reverse=False)
    result = json_load(result_str)
    if result.get("result", {}).get("status") != "OK":
        query_type = result.get("query", {}).get("type", "<Unknown>")
        query = result.get("query", {}).get("query", "<Unknown>")
        error_msg = result.get("result", {}).get(
            "msg", f"Faulty response: {result_str}")
        raise ValueError(f"{query_type} query '{query}' failed: {error_msg}")
    if records:
        pkg_records = []
        for pkg in result["result"]["pkgs"]:
            record = PackageRecord(**pkg)
            pkg_records.append(record)
        return sorted(pkg_records, key=lambda rec: (rec.name, rec.version, rec.build), reverse=False)
    return result


def _search(spec, channels, subdirs, key=None):
    if get_solver_key(key=key) == "classic":
        return sorted(SubdirData.query_all(spec, channels, subdirs),
                      key=lambda rec: (rec.name, VersionOrder(rec.version), rec.build))
    try:
        from conda_libmamba_solver.solver import LibMambaIndexHelper
    except ImportError:
        return sorted(SubdirData.query_all(spec, channels, subdirs),
                      key=lambda rec: (rec.name, VersionOrder(rec.version), rec.build))
    index = LibMambaIndexHelper([], channels, subdirs)
    query = spec.original_spec_str
    return _process_query_result(index.search(query))


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
    matches = _search(spec, channel_urls, subdirs, key=args.solver)
    if not matches and spec.get_exact_value("name"):
        flex_spec = MatchSpec(spec, name="*%s*" % spec.name)
        if not context.json:
            print("No match found for: %s. Search: %s" % (spec, flex_spec))
        matches = _search(flex_spec, channel_urls, subdirs, key=args.solver)
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
        builder = ['\n# %-18s %15s %30s  %-20s' % (
            "Name",
            "Version",
            "Build",
            "Channel",
        )]
        for record in matches:
            builder.append('%-20s %15s %30s  %-20s' % (
                record.name,
                record.version,
                record.build,
                record.channel.name,
            ))
        print('\n'.join(builder))
