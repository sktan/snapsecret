import os
from concurrent.futures import ThreadPoolExecutor

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault("SECRETS_TABLE", "secrets-table")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

import snapsecret  # noqa: E402


@pytest.fixture
def dynamodb_table():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName=os.environ["SECRETS_TABLE"],
            KeySchema=[{"AttributeName": "secret_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "secret_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield dynamodb.Table(os.environ["SECRETS_TABLE"])


def test_retrieve_secret_value_is_single_use(dynamodb_table):
    secret_id = snapsecret.store_secret_value("my-secret")

    first = snapsecret.retrieve_secret_value(secret_id)
    second = snapsecret.retrieve_secret_value(secret_id)

    assert first == "my-secret"
    assert second is None


def test_retrieve_secret_value_missing_id_returns_none(dynamodb_table):
    assert snapsecret.retrieve_secret_value("does-not-exist") is None


def test_retrieve_secret_value_expired_returns_none(dynamodb_table, monkeypatch):
    monkeypatch.setattr(snapsecret, "get_unix_timestamp", lambda add_hours=0: 1000)
    secret_id = snapsecret.store_secret_value("my-secret")

    monkeypatch.setattr(snapsecret, "get_unix_timestamp", lambda add_hours=0: 2000)

    assert snapsecret.retrieve_secret_value(secret_id) is None


def test_concurrent_retrieve_only_succeeds_once(dynamodb_table):
    secret_id = snapsecret.store_secret_value("my-secret")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(snapsecret.retrieve_secret_value, secret_id)
            for _ in range(2)
        ]
        results = [future.result() for future in futures]

    successes = [result for result in results if result == "my-secret"]
    failures = [result for result in results if result is None]

    assert len(successes) == 1
    assert len(failures) == 1
