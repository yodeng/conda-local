#!/usr/bin/env python
# coding:utf-8


from ..src import *


def configure_parser(sub_parsers, name="list"):
    help_desc = "List all available (cached) local conda repodata."
    if name != "list":
        help_desc = "Alias for list"
    example = dedent("""
        Examples:
        
            conda local {}
        """.format(name))
    p = sub_parsers.add_parser(
        name,
        help=help_desc,
        epilog=example,
    )
    p.add_argument(
        '-c', '--channel',
        dest='channel',
        action="append",
        help="show all packages of this cached channel",
    )
    p.add_argument(
        '--only-channel-name',
        action="store_true",
        default=False,
        help="only show cached channel names",
    )
    add_logging_debug(p)
    p.set_defaults(func='.cli.main_list.execute')


def execute(args):
    localrepo = LocalCondaRepo()
    localrepo.parse_repos()
    if args.only_channel_name:
        print("all local cached channels:")
        for cn in sorted(localrepo.channels.keys()):
            print("  - {}".format(cn))
        sys.exit()
    chn_info = nested_dict()
    cached_chns = [basename(dirname(dirname(rf))) for rf in localrepo.repos]
    if args.channel:
        for c in args.channel:
            if c in cached_chns:
                break
        else:
            raise CondaError("No channel %s cached." % args.channel)
    with Spinner("Load cached conda repodata", fail_message="failed\n"):
        for repofile in localrepo.repos:
            chn = basename(dirname(dirname(repofile)))
            if args.channel and chn not in args.channel:
                continue
            url = localrepo.channels_url[chn]
            chn_info[chn]["url"] = cstring(url, 4, 34)
            try:
                with open(repofile) as fi:
                    repodata = json.load(fi)
            except:
                LOCAL_CONDA_LOG.warn(
                    "Load channel '%s' error, removed this channel.", chn)
                os.remove(repofile)
                continue
            subdir = repodata['info'].get(
                'subdir', basename(dirname(repofile)))
            chn_info[chn]["cached"][subdir] = repodata["packages"]
            chn_info[chn]["packages"][subdir] = len(repodata["packages"])
            chn_info[chn]["size"][subdir] = human_bytes(
                sum([p["size"] for _, p in repodata["packages"].items()]))
        for uf in localrepo.url_files:
            if isfile(uf):
                with open(uf) as fi:
                    info = json.load(fi)
                chn_time = time.strftime(
                    "%F %X", time.localtime(info["time_stmp"]))
                for chn, _ in info["channels"].items():
                    if chn in chn_info:
                        chn_info[chn]["cache time"] = chn_time
        if not len(chn_info):
            raise CondaError(
                "No cached repodata found, you might need to run 'conda local cache'")
    if not args.channel:
        for cn, info in sorted(chn_info.items(), key=lambda x: sum(list(x[1]['packages'].values())), reverse=True):
            print(cstring(cn + ":", 1, 34))
            for k in ['cache time', 'url', 'packages', 'size']:
                if k in ['cache time', "url"]:
                    v = "  - " + k + ": " + info[k]
                    print(v)
                elif k in ['packages', 'size']:
                    print("  - " + k + ":")
                    for arch, value in info[k].items():
                        v = "  " + "  - " + arch + ": " + str(value)
                        print(v)
            print()
    else:
        records = set()
        for c in args.channel:
            if c in chn_info:
                for sub, info in chn_info[c]["cached"].items():
                    for rec in info.values():
                        records.add(
                            (rec["name"], rec["version"], rec["build"], c))
        records = sorted(records, key=lambda x: (
            x[3], x[0], VersionOrder(x[1]), x[2]))
        print('# %-18s %15s %30s  %-20s' %
              ("Name", "Version", "Build", "Channel"))
        for rec in records:
            print('%-20s %15s %30s  %-20s' % (rec[0], rec[1], rec[2], rec[3]))
