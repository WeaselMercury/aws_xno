import os
from argparse import ArgumentParser
from sys import exit

from .introspection import (
    get_listing_operations, get_services
)

from .query import do_query

def main():
    parser = ArgumentParser(
        prog='aws_xno',
        description=(
            'List EC2 resources on one account across regions and operations. '
            'Saves result into json files, which can then be passed to this tool again '
            'to list the contents.'
        )
    )
    subparsers = parser.add_subparsers(
        description='List of subcommands. Use <subcommand> --help for more parameters',
        dest='command',
        metavar='COMMAND'
    )

    query = subparsers.add_parser('query', description='Query AWS for resources', help='Query AWS for resources')
    query.add_argument(
        '--service',
        action='append',
        help='Restrict querying to the given service (can be specified multiple times)'
    )
    query.add_argument(
        '--region',
        action='append',
        help='Restrict querying to the given region (can be specified multiple times)'
    )
    query.add_argument(
        '--operation',
        action='append',
        help='Restrict querying to the given operation (can be specified multiple times)'
    )
    query.add_argument('--directory', default='.', help='Directory to save result listings to')
    query.add_argument('--verbose', action='count', help='Print detailed info during run')

    args = parser.parse_args()

    if args.command == 'query':
        if args.directory:
            try:
                os.makedirs(args.directory)
            except OSError:
                pass
            os.chdir(args.directory)
        services = args.service or get_services()
        do_query(services, args.region, args.operation, verbose=args.verbose or 0)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    exit(main())
