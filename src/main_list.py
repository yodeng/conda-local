#!/usr/bin/env python
# coding:utf-8


from .src import *


def configure_parser(sub_parsers):
    description = "List all available (cached) local conda repodata."
    example = dedent("""
        Examples:
        
            conda local list
        """)
    p = sub_parsers.add_parser(
        'list',
        help=description,
        description=description,
        epilog=example,
    )
    p.set_defaults(func='.main_list.execute')


def execute(args):
    localrepo = LocalCondaRepo()
    localrepo.parse_repos()
    chn_info = nested_dict()
    with Spinner("Load cached conda repodata", fail_message="failed\n"):
        for repofile in localrepo.repos:
            chn = basename(dirname(dirname(repofile)))
            url = localrepo.channels_url[chn]
            chn_info[chn]["url"] = cstring(url, 4, 34)
            with open(repofile) as fi:
                repodata = json.load(fi)
            subdir = repodata['info'].get(
                'subdir', basename(dirname(repofile)))
            chn_info[chn]["packages"][subdir] = len(repodata["packages"])
            chn_info[chn]["size"][subdir] = human_bytes(
                sum([p["size"] for _, p in repodata["packages"].items()]))
        for uf in localrepo.url_files:
            if isfile(uf):
                with open(uf) as fi:
                    info = json.load(fi)
                chn_time = time.strftime(
                    "%F %X", time.gmtime(info["time_stmp"]))
                for chn, _ in info["channels"].items():
                    if chn in chn_info:
                        chn_info[chn]["cache time"] = chn_time
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
