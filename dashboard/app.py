from flask import Flask, render_template, jsonify
from datetime import datetime
from threading import Lock

app = Flask(__name__)

# Local in-memory incident storage
incidents = []
incident_lock = Lock()


def get_statistics():
    with incident_lock:
        total = len(incidents)
        resolved = sum(
            1 for incident in incidents
            if incident["status"] == "RESOLVED"
        )
        active = total - resolved
        critical = sum(
            1 for incident in incidents
            if incident["severity"] == "CRITICAL"
        )

    return {
        "total": total,
        "resolved": resolved,
        "active": active,
        "critical": critical
    }


@app.route("/")
def dashboard():
    with incident_lock:
        incident_data = list(reversed(incidents))

    return render_template(
        "index.html",
        incidents=incident_data,
        stats=get_statistics()
    )


@app.route("/api/incidents")
def get_incidents():
    with incident_lock:
        data = list(reversed(incidents))

    return jsonify(data)


@app.route("/api/simulate/s3", methods=["POST"])
def simulate_s3_incident():
    incident = {
        "id": len(incidents) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": "S3 Public Access Detected",
        "severity": "HIGH",
        "resource": "demo-storage-bucket",
        "status": "SIMULATED",
        "remediation": "Public access block simulation completed"
    }

    with incident_lock:
        incidents.append(incident)

    return jsonify({
        "success": True,
        "message": "S3 security incident simulated.",
        "incident": incident
    })


@app.route("/api/simulate/security-group", methods=["POST"])
def simulate_security_group():
    incident = {
        "id": len(incidents) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": "Unrestricted SSH Access Detected",
        "severity": "CRITICAL",
        "resource": "sg-demo-123456",
        "status": "SIMULATED",
        "remediation": "SSH access restriction simulation completed"
    }

    with incident_lock:
        incidents.append(incident)

    return jsonify({
        "success": True,
        "message": "Security group incident simulated.",
        "incident": incident
    })


@app.route("/api/reset", methods=["POST"])
def reset_incidents():
    with incident_lock:
        incidents.clear()

    return jsonify({
        "success": True,
        "message": "Incident history cleared."
    })


if __name__ == "__main__":
    print("Starting Cloud Security Incident Response Dashboard...")
    print("Open: http://127.0.0.1:5000")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )