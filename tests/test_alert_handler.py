import importlib
import pytest


# Import Lambda handler
module = importlib.import_module(
    "lambda.alert_handler.lambda_function"
)

lambda_handler = module.lambda_handler
analyze_event = module.analyze_event


@pytest.fixture
def sample_event():

    return {
        "source": "aws.s3",
        "region": "ap-south-1",
        "time": "2026-11-19T12:00:00Z",
        "detail": {
            "eventName": "PutBucketPolicy",
            "eventSource": "s3.amazonaws.com",
            "userIdentity": {
                "userName": "test-user"
            },
            "requestParameters": {
                "bucketName": "test-bucket"
            }
        }
    }


def test_event_analysis(sample_event):

    alert = analyze_event(sample_event)

    assert alert["event_name"] == "PutBucketPolicy"
    assert alert["username"] == "test-user"
    assert alert["severity"] == "HIGH"


def test_alert_handler_success(sample_event, monkeypatch):

    monkeypatch.setenv("ALERT_DELIVERY", "console")
    monkeypatch.delenv("SNS_TOPIC_ARN", raising=False)

    result = lambda_handler(sample_event, None)

    assert result["status"] == "success"
    assert result["notification"] == "Console notification generated"


def test_unknown_event(sample_event):

    sample_event["detail"]["eventName"] = "UnknownEvent"

    alert = analyze_event(sample_event)

    assert alert["severity"] == "MEDIUM"


def test_invalid_event():

    result = lambda_handler(None, None)

    assert result["status"] == "error"