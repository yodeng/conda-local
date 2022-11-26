#!/usr/bin/env python
# coding:utf-8

from ..src import *


def configure_parser(sub_parsers):
    description = "Cache local conda repodata."
    example = dedent("""
        Examples:
        
            conda local cache
        """)
    p = sub_parsers.add_parser(
        'cache',
        description=description,
        help=description,
        epilog=example,
    )
    p.add_argument(
        '-q', "--quiet",
        action='store_true',
        default=NULL,
        help="Do not display progress bar.",
    )
    p.add_argument(
        "-m", '--mirror',
        metavar='url',
        nargs='+',
        default=[DEFAULT_MIRROR, ],
        help="conda mirror (Not channel) site, %s by default" % DEFAULT_MIRROR,
    )
    p.set_defaults(func='.cli.main_cache.execute')


def execute(args):
    from hget.utils import loger
    log = loger()
    mirrors = args.mirror
    repo_info = {}
    with Spinner("Find channels repodata from %s" % ", ".join(mirrors), fail_message="failed\n"):
        for ms in mirrors:
            urls = get_repo_urls(mirrors=ms)
            if not len(urls):
                raise CondaError(
                    "%s is not a correct conda mirror url or there is no channels in this mirror." % ms)
            repo_info[ms] = urls
    for ms, info in repo_info.items():
        n = urlsplit(ms)
        md = join(LocalCondaRepo.defaut_repo_dir,
                  n.hostname, n.path.strip("/"))
        url_data = {"channels": {}}
        if os.path.isfile(join(md, ".urls.json")):
            try:
                with open(join(md, ".urls.json")) as fi:
                    url_data = json.load(fi)
            except:
                pass
        for c, arc in info.items():
            for a, repo in arc.items():
                outdir = join(md, c, a)
                outfile = join(outdir, os.path.basename(repo))
                os.makedirs(outdir, exist_ok=True)
                chn = Channel.from_url(repo)
                url_data["channels"][c] = chn.base_url
                if isfile(outfile+".ht"):
                    os.remove(outfile+".ht")
                hget(url=repo, outfile=outfile, quiet=args.quiet)
        url_data["time_stmp"] = int(time.time())
        with open(join(md, ".urls.json"), "w") as fo:
            json.dump(url_data, fo, indent=2)
