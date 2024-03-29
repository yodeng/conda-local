#!/usr/bin/env python
# coding:utf-8

from .src import *
from .cli import *


def create_parser():
    p = localArgumentParser()
    sub_parsers = p.add_subparsers(
        metavar='command',
        dest='cmd',
    )
    main_install.configure_parser(sub_parsers)
    main_create.configure_parser(sub_parsers)
    main_update.configure_parser(sub_parsers)
    main_remove.configure_parser(sub_parsers)
    main_search.configure_parser(sub_parsers)
    main_download.configure_parser(sub_parsers)
    main_cache.configure_parser(sub_parsers)
    main_list.configure_parser(sub_parsers)
    main_list.configure_parser(sub_parsers, name="ls")
    show_help_on_empty_command()
    add_version(p)
    return p


def do_call(args):
    relative_mod, func_name = args.func.rsplit('.', 1)
    module = import_module(relative_mod, __package__)
    ForceExitDaemon().start()
    return getattr(module, func_name)(args)


def main():
    parser = create_parser()
    args = parser.parse_args()
    if getattr(args, "debug", None):
        LOCAL_CONDA_LOG.setLevel(10)
    os.environ["CONDA_AUTO_UPDATE_CONDA"] = "false"
    context.__init__(argparse_args=args)
    try:
        init_loggers(context)
    except TypeError:
        init_loggers()
    stdoutlog = getLogger("conda.stdoutlog")
    for h in stdoutlog.handlers:
        stdoutlog.removeHandler(h)
    return conda_exception_handler(do_call, args)


if __name__ == '__main__':
    sys.exit(main())
