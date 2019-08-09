import boto3

from .client import get_client

PARAMETERS = {
    'ec2': {
        'DescribeSnapshots': {
            'OwnerIds': ['self']
        },
        'DescribeImages': {
            'Owners': ['self']
        },
    },
}


def run_raw_listing_operation(service, region, operation):
    """Execute a given operation and return its raw result"""
    client = get_client(service, region)
    api_to_method_mapping = dict((v, k) for k, v in client.meta.method_to_api_mapping.items())
    parameters = PARAMETERS.get(service, {}).get(operation, {})
    return getattr(client, api_to_method_mapping[operation])(**parameters)


class Listing(object):
    """Represents a listing operation on an AWS service and its result"""

    def __init__(self, service, region, operation, response):
        self.service = service
        self.region = region
        self.operation = operation
        self.response = response

    def to_json(self):
        return {
            'service': self.service,
            'region': self.region,
            'operation': self.operation,
            'response': self.response,
        }


    @property
    def resource_types(self):
        """The list of resource types (Keys with list content) in the response"""
        return list(self.resources.keys())

    @property
    def resource_total_count(self):
        """The estimated total count of resources - can be incomplete"""
        return sum(len(v) for v in self.resources.values())

    def export_resources(self, filename):
        """Export the result to the given JSON file"""
        with open(filename, 'w') as outfile:
            outfile.write(pprint.pformat(self.resources).encode('utf-8'))

    
    @classmethod
    def acquire(cls, service, region, operation):
        """Acquire the given listing by making an AWS request"""
        response = run_raw_listing_operation(service, region, operation)
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise Exception('Bad AWS HTTP Status Code', response)
        return cls(service, region, operation, response)

    @property
    def resources(self):  # pylint:disable=too-many-branches
        """Transform the response data into a dict of resource names to resource listings"""
        response = self.response.copy()
        complete = True

        del response['ResponseMetadata']


        for neutral_thing in ('MaxResults', 'Quantity'):
            if neutral_thing in response:
                del response[neutral_thing]


        # Filter default VPCs
        if self.service == 'ec2' and self.operation == 'DescribeVpcs':
            response['Vpcs'] = [vpc for vpc in response['Vpcs'] if not vpc['IsDefault']]

        # Filter default Subnets
        if self.service == 'ec2' and self.operation == 'DescribeSubnets':
            response['Subnets'] = [net for net in response['Subnets'] if not net['DefaultForAz']]

        # Filter default SGs
        if self.service == 'ec2' and self.operation == 'DescribeSecurityGroups':
            response['SecurityGroups'] = [sg for sg in response['SecurityGroups'] if sg['GroupName'] != 'default']

        # Filter main route tables
        if self.service == 'ec2' and self.operation == 'DescribeRouteTables':
            response['RouteTables'] = [
                rt for rt in response['RouteTables'] if not any(x['Main'] for x in rt['Associations'])
            ]

        # Filter default Network ACLs
        if self.service == 'ec2' and self.operation == 'DescribeNetworkAcls':
            response['NetworkAcls'] = [nacl for nacl in response['NetworkAcls'] if not nacl['IsDefault']]

        # Filter default Internet Gateways
        if self.service == 'ec2' and self.operation == 'DescribeInternetGateways':
            describe_vpcs = run_raw_listing_operation(self.service, self.region, 'DescribeVpcs')
            vpcs = {v['VpcId']: v for v in describe_vpcs.get('Vpcs', [])}
            internet_gateways = []
            for ig in response['InternetGateways']:
                attachments = ig.get('Attachments', [])
                # more than one, it cannot be default.
                if len(attachments) != 1:
                    continue
                vpc = attachments[0].get('VpcId')
                if not vpcs.get(vpc).get('IsDefault', False):
                    internet_gateways.append(ig)
            response['InternetGateways'] = internet_gateways

        # Filter Public images from ec2.fpga images
        if self.service == 'ec2' and self.operation == 'DescribeFpgaImages':
            response['FpgaImages'] = [image for image in response.get('FpgaImages', []) if not image.get('Public')]


        for key, value in response.items():
            if not isinstance(value, list):
                raise Exception('No listing: {} is no list:'.format(key), response)

        if not complete:
            response['truncated'] = [True]

        return response
