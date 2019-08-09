from json import load
import boto3
from pkg_resources import resource_stream

from app_json_file_cache import AppCache

from .client import get_client

cache = AppCache('aws_xno')

DESCRIBING = ['Describe']

AWS_RESOURCE_QUERIES = {
   
    'ec2': [
        'DescribePrefixLists', 'DescribeAvailabilityZones', 'DescribeVpcEndpointServices', 'DescribeSpotPriceHistory',
        'DescribeHostReservationOfferings', 'DescribeRegions', 'DescribeReservedInstancesOfferings', 'DescribeIdFormat',
        'DescribeVpcClassicLinkDnsSupport', 'DescribeAggregateIdFormat'
    ],
   
}

NOT_RESOURCE_DESCRIPTIONS = {
    
    'ec2': [
        'DescribeAccountAttributes', 'DescribeDhcpOptions', 'DescribeVpcClassicLink',
        'DescribeVpcClassicLinkDnsSupport', 'DescribePrincipalIdFormat'
    ],
    
}

PARAMETERS_REQUIRED = {
    
    'ec2': ['DescribeSpotDatafeedSubscription', 'DescribeLaunchTemplateVersions'],
    
}


def get_services():
    """Return a list of all service names where listable resources can be present"""
    return [service for service in boto3.Session().get_available_services()]


def get_listing_operations(service, region=None, selected_operations=()):
    """Return a list of API calls which (probably) list resources created by the user
    in the given service (in contrast to AWS-managed or default resources)"""
    client = get_client(service, region)
    operations = []
    for operation in client.meta.service_model.operation_names:
        if not any(operation.startswith(prefix) for prefix in DESCRIBING):
            continue
        op_model = client.meta.service_model.operation_model(operation)
        if op_model.input_shape and op_model.input_shape.required_members:
            continue
        if operation in PARAMETERS_REQUIRED.get(service, []):
            continue
        if operation in AWS_RESOURCE_QUERIES.get(service, []):
            continue
        if operation in NOT_RESOURCE_DESCRIPTIONS.get(service, []):
            continue
        if selected_operations and operation not in selected_operations:
            continue
        operations.append(operation)
    return operations


def packaged_endpoint_hosts():
    return load(resource_stream(__package__, 'endpoint_hosts.json'))['data']


def packaged_service_regions():
    return load(resource_stream(__package__, 'service_regions.json'))['data']


@cache('service_regions', vary={'boto3_version': boto3.__version__}, cheap_default_func=packaged_service_regions)
def get_service_regions():
    service_regions = {}

    return {service: list(regions) for service, regions in service_regions.items()}


def get_regions_for_service(requested_service, requested_regions=()):
    """Given a service name, return a list of region names where this service can have resources,
    restricted by a possible set of regions."""
    regions = set(get_service_regions()[requested_service])
    return list(regions) if not requested_regions else list(sorted(set(regions) & set(requested_regions)))