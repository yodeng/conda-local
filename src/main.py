#!/usr/bin/env python
# coding:utf-8

from .src import *

from . import main_create
from . import main_update
from . import main_search
from . import main_remove
from . import main_install
from . import main_listrepo
from . import main_cacherepo


def create_parser():
    p = localArgumentParser()
    sub_parsers = p.add_subparsers()
    main_install.configure_parser(sub_parsers)
    main_create.configure_parser(sub_parsers)
    main_update.configure_parser(sub_parsers)
    main_remove.configure_parser(sub_parsers)
    main_search.configure_parser(sub_parsers)
    main_cacherepo.configure_parser(sub_parsers)
    main_listrepo.configure_parser(sub_parsers)
    show_help_on_empty_command()
    add_version(p)
    return p


def do_call(args):
    relative_mod, func_name = args.func.rsplit('.', 1)
    module = import_module(relative_mod, __name__.rsplit('.', 1)[0])
    return getattr(module, func_name)(args)


def main():
    parser = create_parser()
    args = parser.parse_args()
    os.environ["CONDA_AUTO_UPDATE_CONDA"] = "false"
    context.__init__(argparse_args=args)
    init_loggers(context)
    return conda_exception_handler(do_call, args)


if __name__ == '__main__':
    sys.exit(main())
