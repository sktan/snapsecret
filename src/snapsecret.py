from datetime import datetime, timezone, timedelta
from typing import Union
import base64
import json
import os
import secrets
import boto3
import logging

from botocore.exceptions import ClientError

# Enables type hinting but only during development
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource
else:
    DynamoDBServiceResource = object


def build_response(
    event: dict, status_code: int = 200, body: Union[str, dict] = None
) -> dict:
    """Builds the response for the Lambda function

    Args:
        event (dict): The event that triggered the Lambda function
        status_code (int): The HTTP status code
        body (str,dict): The body of the response

    Returns:
        The response for the Lambda function
    """

    response = {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
    }

    cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
    origin = event.get("headers", {}).get("origin")
    if "*" in cors_origins or origin in cors_origins:
        # Use origin header as header response resolved from lambda event
        response["headers"]["Access-Control-Allow-Origin"] = origin
        response["headers"]["Access-Control-Allow-Methods"] = "GET,PUT"

    if body and type(body) is str:
        response["body"] = body
    elif body and type(body) is dict:
        response["body"] = json.dumps(body)

    return response


def get_unix_timestamp(add_hours: int = 0) -> int:
    """Returns the calculated unix timestamp

    Args:
        add_hours (int, optional): The number of hours to add to the current time. Defaults to 0.

    Returns:
        The calculated unix timestamp after adding any optional hours
    """
    dt = datetime.now(timezone.utc) + timedelta(hours=add_hours)
    return int(dt.timestamp())


def store_secret_value(value: str) -> str:
    """Stores the secret value into the DynamoDB table

    Args:
        value (str): The secret value to store

    Returns:
        The id that was used to store the secret that we can reference in the subsequent GET request
    """

    dynamodb: DynamoDBServiceResource = boto3.resource("dynamodb")
    secret_id = secrets.token_urlsafe(32)
    table = dynamodb.Table(os.environ.get("SECRETS_TABLE"))

    expires_at = get_unix_timestamp(add_hours=24)

    table.put_item(
        Item={
            "secret_id": secret_id,
            "expires_at": expires_at,
            "value": value,
        }
    )

    return secret_id


def retrieve_secret_value(secret_id: str) -> str:
    """Retrieves the secret value from the DynamoDB table
    This will also delete the item from the table if it exists

    Args:
        secret_id (str): The secret id to retrieve

    Returns:
        The secret value
    """

    dynamodb: DynamoDBServiceResource = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ.get("SECRETS_TABLE"))

    response = table.get_item(Key={"secret_id": secret_id})

    if "Item" not in response:
        return None

    item = response["Item"]

    # delete item since it's supposed to be a OTA
    table.delete_item(Key={"secret_id": secret_id})

    if item["expires_at"] < get_unix_timestamp():
        return None

    return item["value"]


def is_base64(input: str) -> bool:
    """Checks if the string is a base64 string

    Args:
        input (str): The string to check

    Returns:
        True if the string is a base64 string, False otherwise
    """
    try:
        return base64.b64decode(input, validate=True) != None
    except:
        return False


def get_secret_file(event: dict, secret: dict) -> dict:
    get_url = get_s3_presigned_url("GET", secret["object_key"])
    delete_url = get_s3_presigned_url("DELETE", secret["object_key"])

    secret["get_url"] = get_url
    secret["delete_url"] = delete_url

    return build_response(event=event, body={"secret": secret})


def get_secret(event: dict):
    """Handles the HTTP response for a GET request to the /secret/:secret_id endpoint

    Args:
        event (dict): The event that triggered the Lambda function
    """

    secret_id: str = str(event["pathParameters"]["secret_id"])

    if len(secret_id) != 43:
        return build_response(event=event, status_code=404)
    if not secret_id.replace("-", "").replace("_", "").isalnum():
        return build_response(event=event, status_code=404)

    if secret := retrieve_secret_value(secret_id):
        if {"object_key", "iv", "salt", "file_name"} <= secret.keys():
            return get_secret_file(event=event, secret=secret)
        return build_response(event=event, body={"secret": secret})

    return build_response(event=event, status_code=404)


def put_secret(event: dict) -> dict:
    """Handles the HTTP response for a PUT request to the /secret/ endpoint

    Args:
        event (dict): The event that triggered the Lambda function
    """

    post_data = json.loads(event["body"])

    # Check if secret.secret, secret.iv, secret.salt was provided
    secret_value = post_data.get("secret")
    if not secret_value or (
        not {"secret", "iv", "salt"} <= secret_value.keys()
        and not {"object_key", "iv", "salt", "file_name"} <= secret_value.keys()
    ):
        return build_response(
            event=event, status_code=400, body={"error": "Missing secret value"}
        )
    # check if base64 string
    if (
        {"secret", "iv", "salt"} <= secret_value.keys()
        and not (
            is_base64(secret_value["secret"])
            and is_base64(secret_value["iv"])
            and is_base64(secret_value["salt"])
        )
    ) or (
        {"object_key", "iv", "salt", "file_name"} <= secret_value.keys()
        and not (
            secret_value["object_key"].replace("-", "").replace("_", "").isalnum()
            and is_base64(secret_value["iv"])
            and is_base64(secret_value["salt"])
            and is_base64(secret_value["file_name"]),
        )
    ):
        return build_response(
            event=event, status_code=400, body={"error": "Invalid secret value"}
        )

    secret_id = store_secret_value(secret_value)

    return build_response(event=event, body={"secret_id": secret_id})


def get_new_file(event: dict) -> dict:
    object_key = secrets.token_urlsafe(32)
    put_url = get_s3_presigned_url("PUT", object_key)

    return build_response(
        event=event, body={"put_url": put_url, "object_key": object_key}
    )


def get_s3_presigned_url(method: str, object_key: str) -> str:
    bucket = os.environ.get("SECRETS_BUCKET")
    expiration = 3600

    client_methods = {
        "PUT": "put_object",
        "GET": "get_object",
        "DELETE": "delete_object",
    }

    s3_client = boto3.client(
        "s3",
        endpoint_url=f"https://s3.{os.environ.get('AWS_REGION')}.amazonaws.com",
    )
    try:
        response = s3_client.generate_presigned_url(
            ClientMethod=client_methods[method],
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=expiration,
            HttpMethod=method,
        )
    except ClientError as e:
        logging.error(e)

    return response


def handler(event: dict, context: dict) -> dict:
    if event["path"].startswith("/secret"):
        """Handles the HTTP response for requests to the /secret/:secret_id? endpoint"""
        if event["httpMethod"] == "GET":
            return get_secret(event)

        if event["httpMethod"] == "PUT":
            return put_secret(event)

    if event["path"].startswith("/file"):
        """Handles the HTTP response for requests to the /file/ endpoint"""

        if event["httpMethod"] == "GET":
            return get_new_file(event)

    return build_response(event=event, status_code=405)
