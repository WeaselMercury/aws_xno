import json
import sys
from collections import defaultdict
from datetime import datetime
from functools import partial
from multiprocessing.pool import ThreadPool
from random import shuffle
from traceback import print_exc

from .introspection import get_listing_operations, get_regions_for_service

from .listing import Listing

RESULT_NOTHING = '---'
RESULT_SOMETHING = '+++'
RESULT_ERROR = '!!!'
RESULT_NO_ACCESS = '>:|'

RESULT_IGNORE_ERRORS = {
    
    'ec2': {
        # ec2 FPGAs not available in all advertised regions
        'DescribeFpgaImages':
            'not valid for this web service',
        # Need to register as a seller to get this listing
        'DescribeReservedInstancesListings':
            'not authorized to use the requested product. Please complete the seller registration',
        # This seems to be the error if no ClientVpnEndpoints are available in the region
        'DescribeClientVpnEndpoints':
            'InternalError',
    },
    
}

NOT_AVAILABLE_FOR_REGION_STRINGS = [
    'is not supported in this region',
    'is not available in this region',
    'not supported in the called region.',
    'Operation not available in this region',
    'Credential should be scoped to a valid region,',
]

NOT_AVAILABLE_FOR_ACCOUNT_STRINGS = [
    'This request has been administratively disabled',
    'Your account isn\'t authorized to call this operation.',
    'AWS Premium Support Subscription is required',
    'not subscribed to AWS Security Hub',
    'is not authorized to use this service',
    'Account not whitelisted',
]

NOT_AVAILABLE_STRINGS = NOT_AVAILABLE_FOR_REGION_STRINGS + NOT_AVAILABLE_FOR_ACCOUNT_STRINGS


def do_query(services, selected_regions=(), selected_operations=(), verbose=0):
    """For the given services, execute all selected operations (default: all) in selected regions
    (default: all)"""
    to_run = []
    print('Building set of queries to execute...')
    for service in services:
        for region in get_regions_for_service(service, selected_regions):
            for operation in get_listing_operations(service, region, selected_operations):
                if verbose > 0:
                    print('Service: {: <28} | Region: {:<15} | Operation: {}'.format(service, region, operation))

                to_run.append([service, region, operation])
    shuffle(to_run)  # Distribute requests across endpoints
    results_by_type = defaultdict(list)
    print('...done. Executing queries...')
    for result in ThreadPool(32).imap_unordered(partial(acquire_listing, verbose), to_run):
        results_by_type[result[0]].append(result)
        if verbose > 1:
            print('ExecutedQueryResult: {}'.format(result))
        else:
            print(result[0][-1], end='')
            sys.stdout.flush()
    print('...done')
    for result_type in (RESULT_NOTHING, RESULT_SOMETHING, RESULT_NO_ACCESS, RESULT_ERROR):
        for result in sorted(results_by_type[result_type]):
            print(*result)


def acquire_listing(verbose, what):
    """Given a service, region and operation execute the operation, serialize and save the result and
    return a tuple of strings describing the result."""
    service, region, operation = what
    try:
        if verbose > 1:
            print(what, 'starting request...')
        listing = Listing.acquire(service, region, operation)
        if verbose > 1:
            print(what, '...request successful.')
        if listing.resource_total_count > 0:
            with open('{}_{}_{}.json'.format(service, operation, region), 'w') as jsonfile:
                json.dump(listing.to_json(), jsonfile, default=datetime.isoformat)
            return (RESULT_SOMETHING, service, region, operation, ', '.join(listing.resource_types))
        else:
            return (RESULT_NOTHING, service, region, operation, ', '.join(listing.resource_types))
    except Exception as exc:  # pylint:disable=broad-except
        if verbose > 1:
            print(what, '...exception:', exc)
        if verbose > 2:
            print_exc()
        result_type = RESULT_NO_ACCESS if 'AccessDeniedException' in str(exc) else RESULT_ERROR

        ignored_err = RESULT_IGNORE_ERRORS.get(service, {}).get(operation)
        if ignored_err is not None:
            if not isinstance(ignored_err, list):
                ignored_err = list(ignored_err)
            for ignored_str_err in ignored_err:
                if ignored_str_err in str(exc):
                    result_type = RESULT_NOTHING

        for not_available_string in NOT_AVAILABLE_STRINGS:
            if not_available_string in str(exc):
                result_type = RESULT_NOTHING

        return (result_type, service, region, operation, repr(exc))