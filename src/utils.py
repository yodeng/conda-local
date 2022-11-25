import os
import re
import sys
import time
import json
import hashlib
import requests

from hget import hget
from lxml import etree
from threading import Lock
from textwrap import dedent
from argparse import ArgumentParser, SUPPRESS
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from logging import getLogger
from importlib import import_module
from collections import defaultdict
from urllib.parse import urlsplit, urlunsplit
from os.path import abspath, dirname, basename, exists, isdir, isfile, join

from conda.cli import common
from conda.cli.main import init_loggers
from conda.cli.main_search import pretty_record
from conda.cli.conda_argparse import add_parser_prefix, ArgumentParser as CondaArgumentParser

from conda.common.url import path_to_url
from conda.common.constants import NULL
from conda.common.io import ProgressBar, Spinner
from conda.common.path import paths_equal, is_package_file, strip_pkg_extension

from conda.core.solve import Solver
from conda.core.subdir_data import SubdirData
from conda.core.prefix_data import PrefixData
from conda.core.index import calculate_channel_urls
from conda.core.link import PrefixSetup, UnlinkLinkTransaction
from conda.core.path_actions import CacheUrlAction, ExtractPackageAction
from conda.core.package_cache_data import PackageCacheData

from conda.base.context import context, determine_target_prefix
from conda.base.constants import UpdateModifier, ROOT_ENV_NAME

from conda._vendor.toolz import concat
from conda._vendor.boltons.setutils import IndexedSet

from conda.gateways.logging import initialize_logging
from conda.gateways.disk.read import lexists
from conda.gateways.disk.test import is_conda_environment
from conda.gateways.disk.create import extract_tarball
from conda.gateways.disk.delete import rm_rf, delete_trash, path_is_clean

from conda.models.match_spec import MatchSpec
from conda.models.version import VersionOrder
from conda.models.channel import Channel, all_channel_urls

from conda.auxlib.ish import dals
from conda.notices import notices
from conda.utils import human_bytes
from conda.misc import explicit, touch_nonadmin
from conda.exceptions import (UnsatisfiableError,
                              DryRunExit,
                              CondaError,
                              CondaValueError,
                              PackagesNotFoundError,
                              NoBaseEnvironmentError,
                              ChecksumMismatchError,
                              PackageNotInstalledError,
                              EnvironmentLocationNotFound,
                              DirectoryNotACondaEnvironmentError,
                              conda_exception_handler)

from ._version import __version__

DEFAULT_THREADS = 10
REPODATA_FN = "repodata.json"
DEFAULT_MIRROR = "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud"
LOCAL_CONDA_LOG = getLogger('conda.stdout')


def flatten(x):
    return [y for l in x for y in flatten(
        l)] if isinstance(x, list) else [x]


def add_version(p):
    p.add_argument("-v", '--version',
                   action='version', version="v" + __version__
                   )


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


def download(url, target_full_path, **kwargs):
    if isfile(target_full_path) and os.path.getsize(target_full_path) == kwargs.get("size", 0):
        if check_md5(target_full_path) != kwargs.get("md5", ""):
            os.remove(target_full_path)
        else:
            return
    hget(url, target_full_path, quiet=True)


def check_md5(filename):
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


def nested_dict():
    return defaultdict(nested_dict)


def show_help_on_empty_command():
    if len(sys.argv) == 1:
        sys.argv.append('--help')


class Log(object):

    @property
    def log(self):
        return getLogger('conda.stdout')


def cstring(string, mode=0, fore=37, back=40):
    s = '\x1b[%s;%s;%sm%s\x1b[0m'
    return s % (mode, fore, back, string)


def get_repo_urls(mirrors=DEFAULT_MIRROR, repodata_fn=REPODATA_FN):
    repo_urls = nested_dict()
    res = requests.get(url=mirrors)
    h = etree.HTML(res.content)
    chn = [i for i in h.xpath("//a/@href")
           if re.match("^\w", i) and i.endswith("/")]
    for c in chn:
        c = c.strip("/")
        for a in context.subdirs:
            url = join(mirrors, c, a, repodata_fn)
            r = requests.head(url)
            if r.status_code != 200:
                continue
            try:
                content_length = int(r.headers.get("Content-Length", 0))
            except:
                continue
            else:
                if content_length > 0:
                    repo_urls[c][a] = url
    return repo_urls
