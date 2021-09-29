"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/mrrc-uploader)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import locale
import logging

import pkg_resources

from mrrc import set_logging
from mrrc.constants import PROG, DESCRIPTION
from mrrc.util import exception_message

logger = logging.getLogger('mrrc')


class CLI(object):
    def __init__(self, formatter_class=argparse.HelpFormatter, prog=PROG):
        self.parser = argparse.ArgumentParser(
            prog=prog,
            description=DESCRIPTION,
            formatter_class=formatter_class,
        )
        self.init_parser = None
        self.upload_parser = None
        self.delete_parser = None
        self.gen_parser = None
        self.ls_parser = None

        locale.setlocale(locale.LC_ALL, '')

    def set_arguments(self):
        try:
            version = pkg_resources.get_distribution("mrrc").version
        except pkg_resources.DistributionNotFound:
            version = "GIT"

        exclusive_group = self.parser.add_mutually_exclusive_group()
        exclusive_group.add_argument("-q", "--quiet", action="store_true")
        exclusive_group.add_argument("-v", "--verbose", action="store_true")
        exclusive_group.add_argument("-V", "--version", action="version", version=version)

        subparsers = self.parser.add_subparsers(help='commands')

        self.init_parser = subparsers.add_parser(
            'init',
            usage=f"{PROG} [OPTIONS] init",
            description=''
        )

        self.upload_parser = subparsers.add_parser(
            'upload',
            usage=f"{PROG} [OPTIONS] upload",
            description=''
        )

        self.delete_parser = subparsers.add_parser(
            'delete',
            usage=f"{PROG} [OPTIONS] delete",
            description=''
        )

        self.gen_parser = subparsers.add_parser(
            'gen',
            usage=f"{PROG} [OPTIONS] gen",
            description=''
        )

        self.ls_parser = subparsers.add_parser(
            'ls',
            usage=f"{PROG} [OPTIONS] ls",
            description=''
        )

    def run(self):
        self.set_arguments()
        args = self.parser.parse_args()
        logging.captureWarnings(True)

        if args.verbose:
            set_logging(level=logging.DEBUG)
        elif args.quiet:
            set_logging(level=logging.WARNING)
        else:
            set_logging(level=logging.INFO)
        try:
            args.func(args)
        except AttributeError:
            if hasattr(args, 'func'):
                raise
            else:
                self.parser.print_help()
        except KeyboardInterrupt:
            pass
        except Exception as ex:
            if args.verbose:
                raise
            else:
                logger.error("exception caught: %s", exception_message(ex))


def run():
    cli = CLI()
    cli.run()


if __name__ == '__main__':
    run()