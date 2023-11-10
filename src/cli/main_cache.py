#!/usr/bin/env python
# coding:utf-8

from ..src import *


def configure_parser(sub_parsers):
    help_desc = "Cache local conda repodata."
    example = dedent("""
        Examples:
        
            conda local cache
        """)
    p = sub_parsers.add_parser(
        'cache',
        help=help_desc,
        epilog=example,
    )
    p.add_argument(
        '-q', "--quiet",
        action='store_true',
        default=NULL,
        help="Do not display progress bar.",
    )
    ex = p.add_mutually_exclusive_group(required=False)
    ex.add_argument(
        "-m", '--mirror',
        metavar='url',
        nargs='+',
        default=list(DEFAULT_MIRROR),
        help="conda mirror (Not channel) site, '%s' and '%s' by default" % (
            DEFAULT_MIRROR[0], DEFAULT_MIRROR[1]),
    )
    ex.add_argument(
        '-c', '--channel',
        dest='channel',
        action="append",
        help="channel to cache",
    )
    add_logging_debug(p)
    p.set_defaults(func='.cli.main_cache.execute')


def execute(args):
    mirrors = args.mirror
    repo_info = {}
    localrepo = LocalCondaRepo()
    localrepo.parse_repos()
    channels = []
    if args.channel:
        mirrors = []
        for chn in args.channel:
            if "://" in chn:
                c = LocalChannels.from_url(chn).to_channel(local=False)
            elif chn in localrepo.channels:
                url = localrepo.channels_url[chn]
                c = LocalChannels.from_url(
                    url).to_channel(local=False, name=chn)
            else:
                c = LocalChannels.from_name(chn).to_channel(local=False)
            if c.name in localrepo.channels:
                try:
                    common.confirm_yn("WARNING: conda channel '%s' already cached\n" % c +
                                      "\nUpdate",
                                      default='no',
                                      dry_run=False)

                except CondaSystemExit:
                    continue
            status, ret_code = is_repo_url(c.url())
            if not status:
                raise UnavailableInvalidChannel(c.url(), ret_code)
            channels.append(c)
    for ms in mirrors[:]:
        n = urlsplit(ms)
        md = join(LocalCondaRepo.defaut_repo_dir,
                  n.hostname or "", n.path)
        if os.path.isfile(join(md, ".urls.json")) and not args.channel:
            try:
                common.confirm_yn("WARNING: conda mirror '%s' already cached\n" % ms +
                                  "\nUpdate",
                                  default='no',
                                  dry_run=False)
            except CondaSystemExit:
                mirrors.remove(ms)
    if mirrors:
        with Spinner("Find channels from %s" % ", ".join(mirrors), fail_message="failed\n"):
            for ms in mirrors:
                chs = get_repo_channels(ms)
                if not len(chs):
                    raise CondaError(
                        "%s is not a correct conda mirror url or there is no channels in this mirror." % ms)
                channels.extend(chs)
    url_cached = {}
    if channels:
        download_args = []
        for c in channels:
            for u in c.urls():
                u = join(u, REPODATA_FN)
                subdir = basename(dirname(u))
                outfile = join(LocalCondaRepo.defaut_repo_dir,
                               c.channel_location, c.name, subdir, REPODATA_FN)
                mkdir(dirname(outfile))
                download_args.append((u, outfile))
            url_file = join(LocalCondaRepo.defaut_repo_dir,
                            c.channel_location, ".urls.json")
            url_cached.setdefault(url_file, {})[c.name] = dirname(c.url())
        if download_args:
            print("\nDownload channels repodata, (%d threads)" %
                  min(DEFAULT_THREADS, len(channels)))
            with ThreadPoolExecutor(DEFAULT_THREADS) as p:
                for url, outfile in download_args:
                    p.submit(Download.download_file, url, outfile)
    if url_cached:
        for f, info in url_cached.items():
            if isfile(f):
                with open(f) as fi:
                    cache = json.load(fi)
                    info.update(cache["channels"])
            mkdir(dirname(f))
            with open(f, "w") as fo:
                data = {"channels": info, "time_stmp": int(time.time())}
                json.dump(data, fo, indent=2)
        LOCAL_CONDA_LOG.info("Cache repodata done.")
