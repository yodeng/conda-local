#!/usr/bin/env python
# coding:utf-8

import os
import re
import sys
import time
import json
import hashlib
import requests
import tempfile

from tqdm import tqdm
from lxml import etree

from textwrap import dedent
from importlib import import_module
from collections import defaultdict
from logging import getLogger, Formatter
from threading import Lock, currentThread, RLock
from urllib.parse import urlsplit, urlunsplit
from argparse import ArgumentParser, SUPPRESS
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from os.path import abspath, dirname, basename, exists, isdir, isfile, join

from conda.cli import common
from conda.cli.main import init_loggers
from conda.cli.main_search import pretty_record
from conda.cli.conda_argparse import add_parser_prefix, ArgumentParser as CondaArgumentParser

from conda.common.io import Spinner
from conda.common.url import path_to_url
from conda.common.constants import NULL
from conda.common.compat import ensure_text_type
from conda.common.path import paths_equal, is_package_file

from conda.core.solve import Solver
from conda.core.path_actions import *
from conda.core.subdir_data import SubdirData
from conda.core.prefix_data import PrefixData
from conda.core.index import calculate_channel_urls
from conda.core.link import PrefixSetup, UnlinkLinkTransaction
from conda.core.package_cache_data import PackageCacheData

from conda.base.context import context, determine_target_prefix
from conda.base.constants import UpdateModifier, ROOT_ENV_NAME

from conda._vendor.toolz import concat
from conda._vendor.boltons.setutils import IndexedSet

from conda.gateways.logging import StdStreamHandler
from conda.gateways.disk.test import is_conda_environment
from conda.gateways.disk.delete import rm_rf, delete_trash, path_is_clean

from conda.models.match_spec import MatchSpec
from conda.models.version import VersionOrder
from conda.models.channel import Channel, all_channel_urls

from conda.auxlib.ish import dals
from conda.utils import human_bytes
from conda.misc import explicit, touch_nonadmin
from conda.exceptions import *

from ._version import __version__

DEFAULT_THREADS = 10
REPODATA_FN = "repodata.json"
DEFAULT_MIRROR = (
    "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud",
    "https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs",
)


def _get_log():
    logger = getLogger("localconda")
    handler = StdStreamHandler("stdout")
    handler.setLevel(20)
    handler.setFormatter(Formatter('[%(levelname)s %(asctime)s] %(message)s'))
    logger.addHandler(handler)
    return logger


LOCAL_CONDA_LOG = _get_log()

default_headers = {
    'Connection': 'close',
    'Accept-Encoding': 'identity',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'
}


def flatten(x):
    return [y for l in x for y in flatten(
        l)] if isinstance(x, list) else [x]


def add_version(p):
    p.add_argument("-v", '--version',
                   action='version', version="v" + __version__
                   )


def add_parse_no_default_channels(p):
    p.add_argument("--without-default-channels", action="store_true", default=False,
                   help="Do not search default or %s/.condarc channels. Requires -c / --channel." % os.getenv(
                       "HOME", os.path.expanduser("~"))
                   )


def add_parser_local_solver(p):
    """
    Add a command-line flag for alternative solver backends.

    See ``context.experimental_solver`` for more info.

    TODO: This will be replaced by a proper plugin mechanism in the future.
    """
    p.add_argument(
        "-s",
        "--solver",
        dest="solver",
        choices=["classic", "libmamba", "libmamba-draft"],
        help="Choose which solver backend to use.",
        default=NULL,
    )


def new_channel_names(channels, args):
    chl_names = list(channels)
    if hasattr(args, "without_default_channels") and args.without_default_channels:
        if hasattr(args, "channel") and not args.channel:
            raise ArgumentError(
                "At least one -c / --channel flag must be supplied when using --without-default-channels.")
        if "defaults" in chl_names:
            chl_names.remove("defaults")
    return tuple(chl_names)


def fast_url(urls):
    delt = 60
    time_record = []
    for url in urls:
        u = urlsplit(url)
        url_base = urlunsplit((u.scheme, u.netloc, "", "", ""))
        start = time.time()
        res = requests.get(url_base)
        if res.status_code != 404:
            delt = time.time() - start
        time_record.append((url, delt))
    return [i[0] for i in sorted(time_record, key=lambda x:float(x[1]))]


def get_md5(filename):
    hm = hashlib.md5()
    if not os.path.isfile(filename):
        return ""
    with open(filename, "rb") as fi:
        while True:
            b = fi.read(10240)
            if not b:
                break
            hm.update(b)
    return hm.hexdigest()


def mkdir(path):
    if not isdir(path):
        os.makedirs(path)


def nested_dict():
    return defaultdict(nested_dict)


def show_help_on_empty_command():
    if len(sys.argv) == 1:
        sys.argv.append('--help')


class Log(object):

    @property
    def log(self):
        return getLogger('localconda')


def cstring(string, mode=0, fore=37):
    s = '\033[%sm\033[%sm%s\033[0m'
    return s % (mode, fore, string)


def get_repo_urls(mirrors=DEFAULT_MIRROR[0], repodata_fn=REPODATA_FN):
    headers = default_headers
    repo_urls = nested_dict()
    res = requests.get(url=mirrors, headers=headers)
    mirrors = res.url
    h = etree.HTML(res.content)
    chn = [i.strip("/") for i in h.xpath("//a/@href")
           if re.match("^\w", i) and i.endswith("/")]
    for c in sorted(chn):
        for a in context.subdirs:
            url = join(mirrors, c, a, repodata_fn)
            r = requests.head(url, headers=headers)
            if r.status_code != 200:
                continue
            try:
                content_length = int(r.headers.get("Content-Length", 0))
            except:
                continue
            else:
                if content_length > 0:
                    repo_urls[c][a]["url"] = url
                    repo_urls[c][a]["size"] = content_length
    return repo_urls


class Download(object):

    bar_format = "{desc}{bar} | {percentage:3.0f}% "

    def __init__(self, axn, exn, lock):
        self.axn = axn
        self.exn = exn
        axn.verify()
        exn.verify()
        self.lock = lock
        self.target_pkgs_dir = axn.target_pkgs_dir
        mkdir(self.target_pkgs_dir)
        self.target_package_cache = PackageCacheData(self.target_pkgs_dir)
        self.headers = default_headers

    def download(self):
        prec_or_spec = self.exn.record_or_spec
        axn = self.axn
        outpath = axn.target_full_path
        url = axn.url
        size = axn.size
        offset = 0
        if isfile(outpath):
            offset = os.path.getsize(outpath)
            if offset == size:
                if get_md5(outpath) == axn.md5:
                    LOCAL_CONDA_LOG.info("%s already esists", outpath)
                    return
                else:
                    os.remove(outpath)
                    offset = 0
        headers = self.headers.copy()
        headers["Range"] = "bytes={}-".format(offset)
        desc = ''
        if prec_or_spec.name and prec_or_spec.version:
            desc = "%s-%s" % (prec_or_spec.name or '',
                              prec_or_spec.version or '')
        size_str = size and human_bytes(size) or ''
        if len(desc) > 0:
            desc = "%-20.20s | " % desc
        if len(size_str) > 0:
            desc += "%-9s | " % size_str
        md5 = hashlib.md5()
        with requests.get(url, headers=headers, stream=True) as res:
            if res.headers.get("Accept-Ranges", "") != "bytes":
                if isfile(outpath):
                    os.remove(outpath)
                    offset = 0
            content_length = float(res.headers.get('Content-Length', 0))
            cur = currentThread()
            pos = None if cur.name == "MainThread" else int(
                cur.name.rsplit("_", 1)[1])
            with tqdm(lock_args=(False,), desc=desc, position=pos, initial=offset, total=content_length, bar_format=self.bar_format, ascii=True, disable=context.quiet) as progress_bar:
                with open(outpath, "ab") as fo:
                    for chunk in res.iter_content(chunk_size=2 ** 14):
                        if chunk:
                            fo.write(chunk)
                            fo.flush()
                            md5.update(chunk)
                            progress_bar.update(len(chunk))
        actual_checksum = md5.hexdigest()
        if actual_checksum != axn.md5:
            LOCAL_CONDA_LOG.debug("md5 mismatch for download: %s (%s != %s)",
                                  url, actual_checksum, axn.md5)
            raise ChecksumMismatchError(
                url, target_full_path, "md5", axn.md5, actual_checksum
            )
        actual_size = os.path.getsize(outpath)
        if actual_size != size:
            LOCAL_CONDA_LOG.debug("size mismatch for download: %s (%s != %s)",
                                  url, actual_size, size)
            raise ChecksumMismatchError(
                url, target_full_path, "size", size, actual_size)
        with self.lock:
            self.target_package_cache._urls_data.add_url(url)

    @classmethod
    def download_file(cls, url, outpath, con_tinue=False):
        chn = basename(dirname(dirname(url)))
        subdir = basename(dirname(url))
        desc = '%-20.20s | ' % (chn + "(%s)" % subdir)
        offset = 0
        if con_tinue and isfile(outpath):
            offset = os.path.getsize(outpath)
        headers = default_headers.copy()
        headers["Range"] = "bytes={}-".format(offset)
        with requests.get(url, headers=headers, stream=True) as res:
            if res.headers.get("Accept-Ranges", "") != "bytes":
                if isfile(outpath):
                    os.remove(outpath)
                    offset = 0
            content_length = float(res.headers.get('Content-Length', 0))
            with tqdm(desc=desc, position=cls.pos, initial=offset, total=content_length, bar_format=cls.bar_format, ascii=True, disable=context.quiet) as progress_bar:
                with open(outpath, "ab") as fo:
                    for chunk in res.iter_content(chunk_size=2 ** 14):
                        if chunk:
                            fo.write(chunk)
                            fo.flush()
                            progress_bar.update(len(chunk))

    def run(self):
        try:
            self.download()
        except Exception as e:
            self.axn.reverse()
            return e
        else:
            self.axn.cleanup()


class Extract(object):

    def __init__(self, exn):
        self.exn = exn
        exn.verify()
        self.target_pkgs_dir = exn.target_pkgs_dir
        mkdir(self.target_pkgs_dir)
        self.target_package_cache = PackageCacheData(self.target_pkgs_dir)

    def extract(self):
        exn = self.exn
        try:
            raw_index_json = read_index_json(exn.target_full_path)
        except (IOError, OSError, JSONDecodeError, FileNotFoundError):
            print("ERROR: Encountered corrupt package tarball at %s. Conda has "
                  "left it in place. Please report this to the maintainers "
                  "of the package." % exn.source_full_path)
            sys.exit(1)
        if isinstance(exn.record_or_spec, MatchSpec):
            url = exn.record_or_spec.get_raw_value('url')
            assert url
            channel = Channel(url) if has_platform(
                url, context.known_subdirs) else Channel(None)
            fn = basename(url)
            sha256 = exn.sha256 or compute_sha256sum(exn.source_full_path)
            size = getsize(exn.source_full_path)
            if exn.size is not None:
                assert size == exn.size, (size, exn.size)
            md5 = exn.md5 or compute_md5sum(exn.source_full_path)
            repodata_record = PackageRecord.from_objects(
                raw_index_json, url=url, channel=channel, fn=fn, sha256=sha256, size=size, md5=md5,
            )
        else:
            repodata_record = PackageRecord.from_objects(
                exn.record_or_spec, raw_index_json)
        repodata_record_path = join(
            exn.target_full_path, 'info', 'repodata_record.json')
        write_as_json_to_file(repodata_record_path, repodata_record)
        package_cache_record = PackageCacheRecord.from_objects(
            repodata_record,
            package_tarball_full_path=exn.source_full_path,
            extracted_package_dir=exn.target_full_path,
        )
        self.target_package_cache.insert(package_cache_record)

    def run(self):
        try:
            self.extract()
        except Exception as e:
            self.exn.reverse()
            raise e
        else:
            self.exn.cleanup()


def Decompress(exn):
    if lexists(exn.target_full_path):
        rm_rf(exn.target_full_path)
    extract_tarball(exn.source_full_path, exn.target_full_path)
