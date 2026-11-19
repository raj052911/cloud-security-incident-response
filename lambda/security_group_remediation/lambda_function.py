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
# DANGEROUS PORTS
# --------------------------------------------------

DANGEROUS_PORTS = {
    22: "SSH",
    3389: "RDP"
}

UNRESTRICTED_CIDRS = {
    "0.0.0.0/0",
    "::/0"
}


# --------------------------------------------------
# EXTRACT SECURITY GROUP ID
# --------------------------------------------------

def extract_security_group_id(event):

    detail = event.get("detail", {})

    parameters = detail.get("requestParameters", {})

    group_id = parameters.get("groupId")

    if not group_id:
        raise ValueError("Security Group ID not found in event")

    return group_id


# --------------------------------------------------
# IDENTIFY RISKY INBOUND RULES
# --------------------------------------------------

def identify_risky_rules(security_group):

    risky_rules = []

    for permission in security_group.get(
        "IpPermissions", []
    ):

        protocol = permission.get("IpProtocol")

        from_port = permission.get("FromPort")
        to_port = permission.get("ToPort")

        # Ignore protocols that cannot be safely classified
        if protocol != "tcp":
            continue

        if from_port != to_port:
            continue

        if from_port not in DANGEROUS_PORTS:
            continue

        for ip_range in permission.get("IpRanges", []):

            cidr = ip_range.get("CidrIp")

            if cidr in UNRESTRICTED_CIDRS:

                risky_rules.append({
                    "protocol": "tcp",
                    "port": from_port,
                    "service": DANGEROUS_PORTS[from_port],
                    "cidr": cidr
                })

        for ip_range in permission.get("Ipv6Ranges", []):

            cidr = ip_range.get("CidrIpv6")

            if cidr in UNRESTRICTED_CIDRS:

                risky_rules.append({
                    "protocol": "tcp",
                    "port": from_port,
                    "service": DANGEROUS_PORTS[from_port],
                    "cidr": cidr
                })

    return risky_rules


# --------------------------------------------------
# SECURITY GROUP REMEDIATION
# --------------------------------------------------

def remediate_security_group(
    group_id,
    ec2_client=None
):

    # Local simulation mode
    if ec2_client is None:

        logger.warning(
            "LOCAL SIMULATION: Security Group remediation for %s",
            group_id
        )

        return {
            "status": "simulated",
            "security_group_id": group_id,
            "action": "Inspect and remove unrestricted SSH/RDP rules"
        }

    # Retrieve Security Group configuration
    response = ec2_client.describe_security_groups(
        GroupIds=[group_id]
    )

    security_groups = response.get(
        "SecurityGroups", []
    )

    if not security_groups:
        raise ValueError("Security Group not found")

    security_group = security_groups[0]

    risky_rules = identify_risky_rules(
        security_group
    )

    if not risky_rules:

        return {
            "status": "no_action_required",
            "security_group_id": group_id,
            "message": "No unrestricted SSH/RDP rules found"
        }

    # Revoke only identified risky rules
    for rule in risky_rules:

        permission = {
            "IpProtocol": rule["protocol"],
            "FromPort": rule["port"],
            "ToPort": rule["port"]
        }

        if ":" in rule["cidr"]:
            permission["Ipv6Ranges"] = [
                {"CidrIpv6": rule["cidr"]}
            ]
        else:
            permission["IpRanges"] = [
                {"CidrIp": rule["cidr"]}
            ]

        ec2_client.revoke_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[permission]
        )

    return {
        "status": "remediated",
        "security_group_id": group_id,
        "removed_rules": risky_rules
    }


# --------------------------------------------------
# MAIN LAMBDA HANDLER
# --------------------------------------------------

def lambda_handler(event, context):

    try:

        if not isinstance(event, dict):
            raise ValueError("Event must be a dictionary")

        group_id = extract_security_group_id(event)

        execution_mode = os.getenv(
            "EXECUTION_MODE",
            "local"
        ).lower()

        ec2_client = None

        if execution_mode == "aws":
            ec2_client = boto3.client("ec2")

        result = remediate_security_group(
            group_id,
            ec2_client
        )

        report = {
            "incident_type": "Security Group Misconfiguration",
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "security_group_id": group_id,
            "remediation": result
        }

        logger.info(
            "Security Group report:\n%s",
            json.dumps(report, indent=4)
        )

        return {
            "status": "success",
            "report": report
        }

    except Exception as error:

        logger.exception(
            "Security Group remediation failed"
        )

        return {
            "status": "error",
            "message": str(error)
        }