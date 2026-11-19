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
# SECURITY EVENT CLASSIFICATION
# --------------------------------------------------

SUSPICIOUS_EVENTS = {
    "PutBucketPolicy": "HIGH",
    "PutBucketAcl": "HIGH",
    "PutBucketPublicAccessBlock": "HIGH",
    "AuthorizeSecurityGroupIngress": "HIGH",
    "RevokeSecurityGroupEgress": "MEDIUM",
    "DeleteTrail": "CRITICAL",
    "StopLogging": "CRITICAL"
}


# --------------------------------------------------
# EVENT ANALYSIS
# --------------------------------------------------

def analyze_event(event):

    detail = event.get("detail", {})

    event_name = detail.get("eventName", "Unknown")
    event_source = detail.get("eventSource", "Unknown")

    user_identity = detail.get("userIdentity", {})

    username = (
        user_identity.get("userName")
        or user_identity.get("principalId")
        or "Unknown"
    )

    severity = SUSPICIOUS_EVENTS.get(
        event_name,
        "MEDIUM"
    )

    alert = {
        "alert_type": "Cloud Security Incident",
        "event_name": event_name,
        "event_source": event_source,
        "username": username,
        "severity": severity,
        "region": event.get("region", "Unknown"),
        "event_time": event.get(
            "time",
            datetime.now(timezone.utc).isoformat()
        ),
        "resource": detail.get("requestParameters", {}),
        "analysis_status": "Suspicious activity detected"
    }

    return alert


# --------------------------------------------------
# SNS NOTIFICATION
# --------------------------------------------------

def send_notification(alert):

    topic_arn = os.getenv("SNS_TOPIC_ARN")

    delivery_mode = os.getenv(
        "ALERT_DELIVERY",
        "console"
    ).lower()

    if delivery_mode != "sns" or not topic_arn:
        logger.warning(
            "LOCAL SECURITY ALERT:\n%s",
            json.dumps(alert, indent=4)
        )

        return "Console notification generated"

    sns = boto3.client("sns")

    sns.publish(
        TopicArn=topic_arn,
        Subject="Cloud Security Incident Alert",
        Message=json.dumps(alert, indent=4)
    )

    return "SNS notification sent successfully"


# --------------------------------------------------
# MAIN LAMBDA HANDLER
# --------------------------------------------------

def lambda_handler(event, context):

    try:

        if not isinstance(event, dict):
            raise ValueError("Event must be a dictionary")

        alert = analyze_event(event)

        notification_status = send_notification(alert)

        response = {
            "status": "success",
            "message": "Security event processed",
            "alert": alert,
            "notification": notification_status
        }

        logger.info(
            "Security event processed successfully"
        )

        return response

    except Exception as error:

        logger.exception(
            "Security alert processing failed"
        )

        return {
            "status": "error",
            "message": str(error)
        }