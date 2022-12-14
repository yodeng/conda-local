#!/usr/bin/env python
# coding:utf-8

from ..src import *
from ..download_and_extract import *


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
    mirrors = args.mirror
    repo_info = {}
    localrepo = LocalCondaRepo()
    localrepo.parse_repos()
    for ms in mirrors:
        n = urlsplit(ms)
        md = join(LocalCondaRepo.defaut_repo_dir,
                  n.hostname, n.path.strip("/"))
        if os.path.isfile(join(md, ".urls.json")):
            common.confirm_yn("WARNING: a conda cached repodata already exists\n"
                              "\nUpdate",
                              default='no',
                              dry_run=False)
    with Spinner("Find channels repodata from %s" % ", ".join(mirrors), fail_message="failed\n"):
        for ms in mirrors:
            urls = get_repo_urls(mirrors=ms)
            if not len(urls):
                raise CondaError(
                    "%s is not a correct conda mirror url or there is no channels in this mirror." % ms)
            repo_info[ms] = urls
    print("\nDownload repodata (%d threads)" % DEFAULT_THREADS)
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
        download_args = []
        for c, arc in info.items():
            for a, repo in arc.items():
                url = repo["url"]
                outdir = join(md, c, a)
                outfile = join(outdir, os.path.basename(url))
                os.makedirs(outdir, exist_ok=True)
                chn = Channel.from_url(url)
                url_data["channels"][c] = chn.base_url
                download_args.append((url, outfile))
        with ThreadPoolExecutor(DEFAULT_THREADS) as p:
            for url, outfile in download_args:
                p.submit(Download.download_file, url, outfile)
        url_data["time_stmp"] = int(time.time())
        with open(join(md, ".urls.json"), "w") as fo:
            json.dump(url_data, fo, indent=2)
    LOCAL_CONDA_LOG.info("Cache repodata done.")
