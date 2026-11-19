import json
import logging
import os
from datetime import datetime, timezone

import boto3


# --------------------------------------------------
# LOGGER CONFIGURATION
# --------------------------------------------------

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# --------------------------------------------------
# S3 PUBLIC ACCESS BLOCK CONFIGURATION
# --------------------------------------------------

PUBLIC_ACCESS_BLOCK_CONFIG = {
    "BlockPublicAcls": True,
    "IgnorePublicAcls": True,
    "BlockPublicPolicy": True,
    "RestrictPublicBuckets": True
}


# --------------------------------------------------
# EXTRACT BUCKET NAME
# --------------------------------------------------

def extract_bucket_name(event):

    detail = event.get("detail", {})

    parameters = detail.get("requestParameters", {})

    bucket_name = parameters.get("bucketName")

    if not bucket_name:
        raise ValueError("S3 bucket name not found in event")

    return bucket_name


# --------------------------------------------------
# S3 REMEDIATION
# --------------------------------------------------

def remediate_public_bucket(bucket_name, s3_client=None):

    # Local simulation: never connects to AWS by default.
    if s3_client is None:

        logger.warning(
            "LOCAL SIMULATION: Public access blocked for %s",
            bucket_name
        )

        return {
            "status": "simulated",
            "bucket_name": bucket_name,
            "action": "Block all public access",
            "configuration": PUBLIC_ACCESS_BLOCK_CONFIG
        }

    # Execute remediation against the supplied S3 client.
    s3_client.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration=PUBLIC_ACCESS_BLOCK_CONFIG
    )

    logger.info(
        "Public access blocked for bucket: %s",
        bucket_name
    )

    return {
        "status": "remediated",
        "bucket_name": bucket_name,
        "action": "All public access restrictions enabled"
    }


# --------------------------------------------------
# MAIN LAMBDA HANDLER
# --------------------------------------------------

def lambda_handler(event, context):

    try:

        if not isinstance(event, dict):
            raise ValueError("Event must be a dictionary")

        bucket_name = extract_bucket_name(event)

        execution_mode = os.getenv(
            "EXECUTION_MODE",
            "local"
        ).lower()

        s3_client = None

        if execution_mode == "aws":
            s3_client = boto3.client("s3")

        remediation_result = remediate_public_bucket(
            bucket_name,
            s3_client
        )

        report = {
            "incident_type": "S3 Public Exposure",
            "bucket_name": bucket_name,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "remediation": remediation_result,
            "overall_status": remediation_result["status"]
        }

        logger.info(
            "Remediation report:\n%s",
            json.dumps(report, indent=4)
        )

        return {
            "status": "success",
            "report": report
        }

    except Exception as error:

        logger.exception("S3 remediation failed")

        return {
            "status": "error",
            "message": str(error)
        }