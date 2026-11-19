import importlib

import boto3
import pytest
from moto import mock_aws


module = importlib.import_module(
    "lambda.s3_remediation.lambda_function"
)

lambda_handler = module.lambda_handler


@pytest.fixture
def s3_client():

    with mock_aws():

        client = boto3.client(
            "s3",
            region_name="ap-south-1"
        )

        client.create_bucket(
            Bucket="test-public-bucket",
            CreateBucketConfiguration={
                "LocationConstraint": "ap-south-1"
            }
        )

        yield client


def test_s3_public_access_remediation(s3_client):

    result = module.remediate_public_bucket(
        "test-public-bucket",
        s3_client
    )

    assert result["status"] == "remediated"

    response = s3_client.get_public_access_block(
        Bucket="test-public-bucket"
    )

    configuration = response[
        "PublicAccessBlockConfiguration"
    ]

    assert configuration["BlockPublicAcls"] is True
    assert configuration["IgnorePublicAcls"] is True
    assert configuration["BlockPublicPolicy"] is True
    assert configuration["RestrictPublicBuckets"] is True


def test_s3_missing_bucket_name():

    event = {
        "detail": {
            "eventName": "PutBucketPolicy",
            "requestParameters": {}
        }
    }

    result = lambda_handler(event, None)

    assert result["status"] == "error"


def test_s3_invalid_event():

    result = lambda_handler(None, None)

    assert result["status"] == "error"