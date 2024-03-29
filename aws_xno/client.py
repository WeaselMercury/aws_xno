import boto3

_CLIENTS = {}

def get_client(service, region=None):
    """Return (cached) boto3 clients for this service and this region"""
    if (service, region) not in _CLIENTS:
        _CLIENTS[(service, region)] = boto3.Session(region_name=region).client(service)
    return _CLIENTS[(service, region)]
