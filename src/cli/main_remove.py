#!/usr/bin/env python
# coding:utf-8

from conda.cli.main_remove import *
from ..src import *


def configure_parser(sub_parsers):
    description = "Remove a list of packages from a specified conda environment."
    example = dedent("""
        Examples:
        
            conda local remove -n myenv pysam
        """)
    name = "remove"
    p = sub_parsers.add_parser(
        'remove',
        description=description,
        help=description,
        epilog=example,
    )
    p.add_argument(
        "-a", "--all",
        action="store_true",
        help="%s all packages, i.e., the entire environment." % name.capitalize(),
    )
    p.add_argument(
        "--force-remove", "--force",
        action="store_true",
        help="Forces removal of a package without removing packages that depend on it. "
             "Using this option will usually leave your environment in a broken and "
             "inconsistent state.",
        dest='force_remove',
    )
    p.add_argument(
        '--dry-run',
        help=('dry run'),
        action='store_true',
        default=False,
    )
    p.add_argument(
        "-y", "--yes",
        action="store_true",
        default=NULL,
        help="Do not ask for confirmation.",
    )
    p.add_argument(
        'package_names',
        metavar='package_name',
        action="store",
        nargs='*',
        help="Package names to %s from the environment." % name,
    )
    add_parser_prefix(p)
    p.set_defaults(func='.cli.main_remove.execute')


def execute(args):
    if not (args.all or args.package_names):
        raise CondaValueError('no package names supplied,\n'
                              '       try "conda local remove -h" for more details')
    prefix = context.target_prefix
    check_non_admin()
    if args.all and prefix == context.default_prefix:
        msg = "cannot remove current environment. deactivate and run conda remove again"
        raise CondaEnvironmentError(msg)
    if args.all and path_is_clean(prefix):
        return 0
    if args.all:
        if prefix == context.root_prefix:
            raise CondaEnvironmentError('cannot remove root environment,\n'
                                        '       add -n NAME or -p PREFIX option')
        if not isfile(join(prefix, 'conda-meta', 'history')):
            raise DirectoryNotACondaEnvironmentError(prefix)
        sys.stderr.write("\nRemove all packages in environment %s:\n" % prefix)
        if 'package_names' in args:
            stp = PrefixSetup(
                target_prefix=prefix,
                unlink_precs=tuple(PrefixData(prefix).iter_records()),
                link_precs=(),
                remove_specs=(),
                update_specs=(),
                neutered_specs={},
            )
            txn = UnlinkLinkTransaction(stp)
            try:
                handle_txn(txn, prefix, args, False, True)
            except PackagesNotFoundError:
                print("No packages found in %s. Continuing environment removal" % prefix)
        if not context.dry_run:
            rm_rf(prefix, clean_empty_parents=True)
            unregister_env(prefix)
        return
    else:
        specs = common.specs_from_args(args.package_names)
        local_repo = LocalCondaRepo()
        local_repo.parse_repos()
        channels = LocalConda.file_channels(context.channels, local_repo)
        LOCAL_CONDA_LOG.info("Using local conda channel: %s", cstring(", ".join(
            flatten([[join(c.base_url if not c.base_url.startswith("file://") else c.base_url[7:], s) for s in context.subdirs] for c in channels])), 0, 34))
        solver = localSolver(prefix, channels,
                             context.subdirs, specs_to_remove=specs)
        txn = solver.solve_for_transaction()
        if txn.nothing_to_do:
            raise PackagesNotFoundError(args.package_names)
        txn.print_transaction_summary()
        if self.args.dry_run:
            raise DryRunExit()
        common.confirm_yn()
        try:
            txn.download_and_extract()
            txn.execute()
        except SystemExit as e:
            raise CondaSystemExit('Exiting', e)
