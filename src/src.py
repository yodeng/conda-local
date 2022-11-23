#!/usr/bin/env python
# coding:utf-8

from .utils import *


class LocalCondaRepo(Log):

    defaut_repo_dir = os.getenv("LOCAL_CONDA_DIR", "") or join(
        os.environ["HOME"], ".conda")
    repodata_fn = REPODATA_FN

    def __init__(self, repo=None):
        self._repodir = [self.defaut_repo_dir]
        if repo and isdir(repo):
            self._repodir.append(os.path.abspath(repo))
        self.repos = []
        self.url_files = set()
        self.channels = {}
        self.channels_url = {}

    def scan_repos(self):
        for rd in self._repodir:
            if isdir(rd):
                for a, b, c in os.walk(rd, followlinks=True):
                    for i in c:
                        if basename(i) == self.repodata_fn:
                            self.repos.append(join(a, i))

    def parse_repos(self):
        if not self.repos:
            self.scan_repos()
        for repo in self.repos:
            subdir = basename(os.path.dirname(repo))
            if subdir in context.subdirs:
                url = path_to_url(os.path.dirname(os.path.dirname(repo)))
                c = Channel.from_url(url)
                self.channels[c.name] = c
                u_file = join(c.channel_location, "urls.txt")
                if isfile(u_file):
                    self.url_files.add(u_file)
        for uf in self.url_files:
            if isfile(uf):
                with open(uf) as fi:
                    self.channels_url.update(json.load(fi)["channels"])
        for c in self.channels.copy():
            if c not in self.channels_url:
                self.channels.pop(c)


class LocalConda(Log):

    def __init__(self, prefix, args):
        self.args = args
        self.prefix = prefix
        self.local_repo = LocalCondaRepo()
        self.solver = None
        self.specs = []

    def _get_spec(self):
        args_packages = [s.strip('"\'') for s in self.args.packages]
        num_cp = sum(is_package_file(s) for s in args_packages)
        if num_cp:
            if num_cp == len(args_packages):
                explicit(args_packages, self.prefix, verbose=not context.quiet)
                return
            else:
                raise CondaValueError("cannot mix specifications with conda package"
                                      " filenames")
        self.specs.extend(common.specs_from_args(
            args_packages, json=context.json))

    def _get_solve(self):
        self.local_repo.parse_repos()
        channels = self.file_channels(context.channels, self.local_repo)
        self.log.info("Using local conda channel: %s", ", ".join(
            flatten([[join(c.location, c.channel_name, s) for s in context.subdirs] for c in channels])))
        solver = _localSolver(self.prefix, channels,
                              context.subdirs, specs_to_add=self.specs)
        return solver

    @staticmethod
    def file_channels(chl_names, local_repo):
        channels = IndexedSet()
        for url in all_channel_urls(chl_names, context.subdirs):
            c = Channel.from_url(url)
            cname = basename(c.name)
            if cname in local_repo.channels and os.path.dirname(local_repo.channels[cname].url()).endswith(c.name):
                channels.add(local_repo.channels[cname])
            else:
                channels.add(c)
        return channels

    def install(self, cmd="install"):
        self._get_spec()
        self.solver = self._get_solve()
        update_modifier = UpdateModifier.FREEZE_INSTALLED
        if cmd == "update":
            update_modifier = context.update_modifier
        try:
            unlink_link_transaction = self.solver.solve_for_transaction(
                deps_modifier=context.deps_modifier,
                force_reinstall=self.args.force_reinstall,
                update_modifier=update_modifier)
        except (UnsatisfiableError, SystemExit):
            unlink_link_transaction = self.solver.solve_for_transaction(
                update_modifier=NULL)
        if unlink_link_transaction.nothing_to_do:
            print('\n# All requested packages already installed.\n')
            return
        unlink_link_transaction.print_transaction_summary()
        if self.args.dry_run:
            raise DryRunExit()
        common.confirm_yn()
        for axn in unlink_link_transaction._pfe.cache_actions:
            self.back_url(axn)
        unlink_link_transaction.download_and_extract()
        unlink_link_transaction.execute()

    def back_url(self, axn):
        c = Channel.from_url(axn.url)
        if c.name in self.local_repo.channels_url and c.base_url in axn.url:
            axn.url = axn.url.replace(
                c.base_url, self.local_repo.channels_url[c.name])

    def create(self):
        if is_conda_environment(self.prefix):
            if paths_equal(self.prefix, context.root_prefix):
                raise CondaValueError(
                    "The target prefix is the base prefix. Aborting.")
            if self.args.dry_run:
                raise CondaValueError(
                    "Cannot `create --dry-run` with an existing conda environment")
            common.confirm_yn("WARNING: A conda environment already exists at '%s'\n"
                              "Remove existing environment" % self.prefix,
                              default='no',
                              dry_run=False)
            print("Removing existing environment %s" % self.prefix)
            rm_rf(self.prefix)
        elif isdir(self.prefix):
            common.confirm_yn("WARNING: A directory already exists at the target location '%s'\n"
                              "but it is not a conda environment.\n"
                              "Continue creating environment" % self.prefix,
                              default='no',
                              dry_run=False)
        check_prefix(self.prefix, json=context.json)
        self.args.force_reinstall = True
        self.install()
        touch_nonadmin(self.prefix)
        print_activate(self.args.name or self.prefix)

    def update(self):
        if context.update_modifier != UpdateModifier.UPDATE_ALL:
            prefix_data = PrefixData(self.prefix)
            for spec in self.specs:
                spec = MatchSpec(spec)
                if not spec.is_name_only_spec:
                    raise CondaError("Invalid spec for 'conda update': %s\n"
                                     "Use 'conda install' instead." % spec)
                if not prefix_data.get(spec.name, None):
                    raise PackageNotInstalledError(prefix, spec.name)
        self.install("update")


class localArgumentParser(CondaArgumentParser, ArgumentParser):

    def print_help(self):
        ArgumentParser.print_help(self)


class _localSolver(Solver):
    def __init__(self, *args, **kwargs):
        super(_localSolver, self).__init__(*args, **kwargs)

    def solve_for_transaction(self, update_modifier=NULL, deps_modifier=NULL, prune=NULL,
                              ignore_pinned=NULL, force_remove=NULL, force_reinstall=NULL,
                              should_retry_solve=False):
        if self.prefix == context.root_prefix and context.enable_private_envs:
            raise NotImplementedError()
        else:
            unlink_precs, link_precs = self.solve_for_diff(update_modifier, deps_modifier,
                                                           prune, ignore_pinned,
                                                           force_remove, force_reinstall,
                                                           should_retry_solve)
            stp = PrefixSetup(self.prefix, unlink_precs, link_precs,
                              self.specs_to_remove, self.specs_to_add, self.neutered_specs)
            return _localUnlinkLinkTransaction(stp)


class _localUnlinkLinkTransaction(UnlinkLinkTransaction):
    def __init__(self, *args, **kwargs):
        super(_localUnlinkLinkTransaction, self).__init__(*args, **kwargs)

    def _get_pfe(self):
        if self._pfe is not None:
            pfe = self._pfe
        elif not self.prefix_setups:
            self._pfe = pfe = _localProgressiveFetchExtract(())
        else:
            link_precs = set(
                concat(stp.link_precs for stp in self.prefix_setups.values()))
            self._pfe = pfe = _localProgressiveFetchExtract(link_precs)
        return pfe


class _localProgressiveFetchExtract(ProgressiveFetchExtract):
    def __init__(self, *args, **kwargs):
        super(_localProgressiveFetchExtract, self).__init__(*args, **kwargs)

    @staticmethod
    def _execute_actions(prec_or_spec, actions):
        cache_axn, extract_axn = actions
        if cache_axn is None and extract_axn is None:
            return
        desc = ''
        if prec_or_spec.name and prec_or_spec.version:
            desc = "%s-%s" % (prec_or_spec.name or '',
                              prec_or_spec.version or '')
        size = getattr(prec_or_spec, 'size', None)
        size_str = size and human_bytes(size) or ''
        if len(desc) > 0:
            desc = "%-20.20s | " % desc
        if len(size_str) > 0:
            desc += "%-9s | " % size_str
        progress_bar = ProgressBar(
            desc, not context.verbosity and not context.quiet, context.json)
        download_total = 1.0
        try:
            if cache_axn:
                cache_axn.verify()
                download_total = 0
                progress_update_cache_axn = None
                cache_axn.execute(progress_update_cache_axn)
            if extract_axn:
                extract_axn.verify()

                def progress_update_extract_axn(pct_completed):
                    progress_bar.update_to(
                        (1 - download_total) * pct_completed + download_total)
                extract_axn.execute(progress_update_extract_axn)
                progress_bar.update_to(1.0)
        except Exception as e:
            if extract_axn:
                extract_axn.reverse()
            if cache_axn:
                cache_axn.reverse()
            return e
        else:
            if cache_axn:
                cache_axn.cleanup()
            if extract_axn:
                extract_axn.cleanup()
            progress_bar.finish()
        finally:
            progress_bar.close()

    @staticmethod
    def make_actions_for_record(pref_or_spec):
        assert pref_or_spec is not None
        sha256 = pref_or_spec.get("sha256")
        size = pref_or_spec.get("size")
        md5 = pref_or_spec.get("md5")
        legacy_bz2_size = pref_or_spec.get("legacy_bz2_size")
        legacy_bz2_md5 = pref_or_spec.get("legacy_bz2_md5")

        def pcrec_matches(pcrec):
            matches = True
            if size is not None and pcrec.get('size') is not None:
                matches = pcrec.size in (size, legacy_bz2_size)
            if matches and md5 is not None and pcrec.get('md5') is not None:
                matches = pcrec.md5 in (md5, legacy_bz2_md5)
            return matches
        extracted_pcrec = next((
            pcrec for pcrec in concat(PackageCacheData(pkgs_dir).query(pref_or_spec)
                                      for pkgs_dir in context.pkgs_dirs)
            if pcrec.is_extracted
        ), None)
        if extracted_pcrec and pcrec_matches(extracted_pcrec) and extracted_pcrec.get('url'):
            return None, None
        pcrec_from_writable_cache = next(
            (pcrec for pcrec in concat(
                pcache.query(pref_or_spec) for pcache in PackageCacheData.writable_caches()
            ) if pcrec.is_fetched),
            None
        )
        if (pcrec_from_writable_cache and pcrec_matches(pcrec_from_writable_cache) and
                pcrec_from_writable_cache.get('url')):
            extract_axn = ExtractPackageAction(
                source_full_path=pcrec_from_writable_cache.package_tarball_full_path,
                target_pkgs_dir=dirname(
                    pcrec_from_writable_cache.package_tarball_full_path),
                target_extracted_dirname=basename(
                    pcrec_from_writable_cache.extracted_package_dir),
                record_or_spec=pcrec_from_writable_cache,
                sha256=pcrec_from_writable_cache.sha256 or sha256,
                size=pcrec_from_writable_cache.size or size,
                md5=pcrec_from_writable_cache.md5 or md5,
            )
            return None, extract_axn
        pcrec_from_read_only_cache = next((
            pcrec for pcrec in concat(pcache.query(pref_or_spec)
                                      for pcache in PackageCacheData.read_only_caches())
            if pcrec.is_fetched
        ), None)
        first_writable_cache = PackageCacheData.first_writable()
        if pcrec_from_read_only_cache and pcrec_matches(pcrec_from_read_only_cache):
            cache_axn = _localCacheUrlAction(
                url=path_to_url(
                    pcrec_from_read_only_cache.package_tarball_full_path),
                target_pkgs_dir=first_writable_cache.pkgs_dir,
                target_package_basename=pcrec_from_read_only_cache.fn,
                sha256=pcrec_from_read_only_cache.get("sha256") or sha256,
                size=pcrec_from_read_only_cache.get("size") or size,
                md5=pcrec_from_read_only_cache.get("md5") or md5,
            )
            trgt_extracted_dirname = strip_pkg_extension(
                pcrec_from_read_only_cache.fn)[0]
            extract_axn = ExtractPackageAction(
                source_full_path=cache_axn.target_full_path,
                target_pkgs_dir=first_writable_cache.pkgs_dir,
                target_extracted_dirname=trgt_extracted_dirname,
                record_or_spec=pcrec_from_read_only_cache,
                sha256=pcrec_from_read_only_cache.get("sha256") or sha256,
                size=pcrec_from_read_only_cache.get("size") or size,
                md5=pcrec_from_read_only_cache.get("md5") or md5,
            )
            return cache_axn, extract_axn
        url = pref_or_spec.get('url')
        assert url
        cache_axn = _localCacheUrlAction(
            url=url,
            target_pkgs_dir=first_writable_cache.pkgs_dir,
            target_package_basename=pref_or_spec.fn,
            sha256=sha256,
            size=size,
            md5=md5,
        )
        extract_axn = ExtractPackageAction(
            source_full_path=cache_axn.target_full_path,
            target_pkgs_dir=first_writable_cache.pkgs_dir,
            target_extracted_dirname=strip_pkg_extension(pref_or_spec.fn)[0],
            record_or_spec=pref_or_spec,
            sha256=sha256,
            size=size,
            md5=md5,
        )
        return cache_axn, extract_axn


class _localCacheUrlAction(CacheUrlAction):
    def __init__(self, *args, **kwargs):
        super(_localCacheUrlAction, self).__init__(*args, **kwargs)

    def _execute_channel(self, target_package_cache, progress_update_callback=None):
        kwargs = {}
        if self.size is not None:
            kwargs["size"] = self.size
        if self.sha256:
            kwargs["sha256"] = self.sha256
        elif self.md5:
            kwargs["md5"] = self.md5
        download(
            self.url,
            self.target_full_path,
            **kwargs
        )
        target_package_cache._urls_data.add_url(self.url)


def check_prefix(prefix, json=False):
    name = basename(prefix)
    error = None
    if name == ROOT_ENV_NAME:
        error = "'%s' is a reserved environment name" % name
    if exists(prefix):
        if isdir(prefix) and 'conda-meta' not in tuple(entry.name for entry in os.scandir(prefix)):
            return None
        error = "prefix already exists: %s" % prefix
    if error:
        raise CondaValueError(error, json)
    if ' ' in prefix:
        LOCAL_CONDA_LOG.warning("WARNING: A space was detected in your requested environment path\n"
                                "'%s'\n"
                                "Spaces in paths can sometimes be problematic." % prefix)


def print_activate(env_name_or_prefix):
    if not context.quiet and not context.json:
        message = dals("""
        #
        # To activate this environment, use
        #
        #     $ conda activate %s
        #
        # To deactivate an active environment, use
        #
        #     $ conda deactivate
        """) % env_name_or_prefix
        print(message)
