import importlib

import boto3
import pytest
from moto import mock_aws


module = importlib.import_module(
    "lambda.security_group_remediation.lambda_function"
)

lambda_handler = module.lambda_handler


@pytest.fixture
def ec2_client():

    with mock_aws():

        client = boto3.client(
            "ec2",
            region_name="ap-south-1"
        )

        response = client.create_security_group(
            GroupName="test-security-group",
            Description="Test security group",
            VpcId="vpc-12345678"
        )

        group_id = response["GroupId"]

        client.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [
                        {"CidrIp": "0.0.0.0/0"}
                    ]
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 3389,
                    "ToPort": 3389,
                    "Ipv6Ranges": [
                        {"CidrIpv6": "::/0"}
                    ]
                }
            ]
        )

        yield client, group_id


def test_security_group_risky_rule_detection(ec2_client):

    client, group_id = ec2_client

    response = client.describe_security_groups(
        GroupIds=[group_id]
    )

    security_group = response["SecurityGroups"][0]

    risky_rules = module.identify_risky_rules(
        security_group
    )

    assert len(risky_rules) == 2

    ports = [
        rule["port"]
        for rule in risky_rules
    ]

    assert 22 in ports
    assert 3389 in ports


def test_security_group_remediation(ec2_client):

    client, group_id = ec2_client

    result = module.remediate_security_group(
        group_id,
        client
    )

    assert result["status"] == "remediated"

    response = client.describe_security_groups(
        GroupIds=[group_id]
    )

    security_group = response["SecurityGroups"][0]

    remaining_rules = module.identify_risky_rules(
        security_group
    )

    assert len(remaining_rules) == 0


def test_security_group_missing_id():

    event = {
        "detail": {
            "eventName": "AuthorizeSecurityGroupIngress",
            "requestParameters": {}
        }
    }

    result = lambda_handler(event, None)

    assert result["status"] == "error"


def test_security_group_invalid_event():

    result = lambda_handler(None, None)

    assert result["status"] == "error"