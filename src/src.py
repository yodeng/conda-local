#!/usr/bin/env python
# coding:utf-8

from .utils import *
from .download_and_extract import *


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
                if c.name in self.channels and c.channel_location != self.channels[c.name].channel_location:
                    LOCAL_CONDA_LOG.debug("duplicate local channels: %s and %s", join(
                        c.channel_location, c.name, subdir), join(self.channels[c.name].channel_location, c.name, subdir))
                self.channels[c.name] = c
                u_file = join(c.channel_location, ".urls.json")
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
        self.lock = Lock()

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
        channel_names = new_channel_names(context.channels, self.args)
        channels = self.file_channels(channel_names, self.local_repo)
        self.log.info("Using local conda channel: %s", cstring(", ".join(
            flatten([[join(c.base_url if not c.base_url.startswith("file://") else c.base_url[7:], s) for s in context.subdirs] for c in channels])), 0, 34))
        solver = localSolver(self.prefix, channels,
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
        if cmd != "create":
            if isdir(self.prefix):
                if not is_conda_environment(self.prefix):
                    raise EnvironmentLocationNotFound(self.prefix)
                delete_trash(self.prefix)
                if not isfile(join(self.prefix, 'conda-meta', 'history')):
                    if paths_equal(self.prefix, context.conda_prefix):
                        raise NoBaseEnvironmentError()
                    else:
                        if not path_is_clean(self.prefix):
                            raise DirectoryNotACondaEnvironmentError(
                                self.prefix)
            else:
                raise EnvironmentLocationNotFound(self.prefix)
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
        self.multi_download_extract(unlink_link_transaction)
        unlink_link_transaction.execute()

    def multi_download_extract(self, txn):
        if len(txn._pfe.cache_actions):
            n_multi = min(len(txn._pfe.cache_actions), DEFAULT_THREADS)
            print("\nDownload Packages")
            with ThreadPoolExecutor(max_workers=n_multi) as p:
                for axn, exn in zip(txn._pfe.cache_actions, txn._pfe.extract_actions):
                    download = Download(axn, exn, self.lock)
                    p.submit(download.run)
            with Spinner("\nExtract Packages", fail_message="failed\n"):
                with ProcessPoolExecutor(max_workers=n_multi) as p:
                    p.map(Decompress, txn._pfe.extract_actions)
                for exn in txn._pfe.extract_actions:
                    estract = Extract(exn)
                    estract.run()
        txn._pfe._executed = True

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
        self.install("create")
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
                    raise PackageNotInstalledError(self.prefix, spec.name)
        self.install("update")


class localArgumentParser(CondaArgumentParser, ArgumentParser):

    def print_help(self):
        ArgumentParser.print_help(self)


class localExceptionHandler(ExceptionHandler):

    def __init__(self, *args, **kwargs):
        super(localExceptionHandler, self).__init__(*args, **kwargs)

    def _calculate_ask_do_upload(self):
        return False, False


def conda_exception_handler(func, *args, **kwargs):
    exception_handler = localExceptionHandler()
    return_value = exception_handler(func, *args, **kwargs)
    return return_value


class localSolver(Solver):

    def __init__(self, *args, **kwargs):
        super(localSolver, self).__init__(*args, **kwargs)

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
            return UnlinkLinkTransaction(stp)


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
