# Snap Secret

[![CodeQL](https://github.com/sktan/snapsecret/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/sktan/snapsecret/actions/workflows/codeql-analysis.yml)

SnapSecret is a simple and easy way to securely send secrets (such as passwords, API keys, etc.) to other people.
This is done by encrypting the secret within your browser with a passphrase before sending it to the backend storage.
This ensures that the backend never receives, stores or retrieves the secret in it's unencrypted form.

This service can be deployed to AWS with minimal costs to operate due to it's serverless nature.

Deployed resources are as follows:
- CloudFront Distribution
- 2x S3 Buckets to store the assets + assets bundle
- DynamoDB
- API Gateway
- 1x Lambda Function (to handle GET and PUT requests to the /secret endpoint)
- KMS (we will be using the dynamodb default kms key)

## Usage

You will first need to submit your secret via the "New Secret" page.
Once completed, your secret will be retrievable via a one time access
(OTA) link that is generated. You can then share this link with the
intended recipient, and they will be able use this to decrypt the
contents. If the recipient does not access the page within 24 hours, it
will automatically self destruct and become invalid.

### Sending the OTA Link

Your are free to send the OTA link via any medium, as there is it is not
considered sensitive data. The preferred way for the decryption
passphrase to be communicated to the recipient is via a separate medium
(e.g. sms, voice call, pre-shared key). Remind the user that the OTA
link will expire in 24 hours, or if it has been accessed by someone
else. If the OTA link has self-destructed prior to 24 hours, you are
recommended to generate a new secret to send as it is possible that it
has been intercepted by another party.

## Encryption / Decryption

All encryption and decryption is done locally on the users browser with the following configuration:

- AES-GCM with a key length of 256
- A salted (16 bytes) PBKDF2 key derived from the user provided passphrase with 100,000 iterations (SHA-256)
- An IV size of 12 bytes

## User Privacy

No cookies, trackers or external scripts are used whilst browsing this website and no user-identifiable data is stored on DynamoDB.

This ensures complete privacy for the sender and receiver when using the service.
Although the general web-access information may be stored as part of CloudFront and API Gateway logs (such as IP address, user agent, etc.).

## Deployment

Deploying this is really easy, due to AWS CDK being used for building and deploying the entire website and backend services.

To deploy the website, you will need the following requirements (already bundled within the Visual Studio Code Devcontainer)
- An AWS account
- AWS CDK v2
- Python 3.9
- Pipenv
- Nodejs
- Docker (to build the website)

```
sktan ➜ ~/repos/sktan/snapsecret (master ✗) $ cd cdk
sktan ➜ ~/repos/sktan/snapsecret/cdk (master ✗) $ npm run bootstrap # only need to run this once
sktan ➜ ~/repos/sktan/snapsecret/cdk (master ✗) $ npm run deploy
```

This will deloy the entire service to AWS automatically without any configuration or building of the frontend on your part.

You are also able to configure your deployment to use a custom domains and certificate for both CloudFront and API Gateway.

This is done via the `cdk/cdk.json` file under the `context` keys:


| Context Key           | Description             |
| --------------------- | ----------------------- |
| parameter_store_api   | The SSM Paramater Store entry for your API Gateway URL (defaults to `/snapsecret/apigateway`)    |
| frontend_domain       | The domain that will point to CloudFront for the WebUI (using this requires `frontend_acm_arn`)  |
| frontend_acm_arn      | The ACM certificate to be used for CloudFront (using this requires `frontend_domain`)            |
| api_domain            | The domain that will point to the API Gateway (using this requires `api_acm_cert`)               |
| api_acm_arn           | The ACM certificate to be used for the API Gateway (using this requires `api_domain`)            |


```
{
  "context": {
      "parameter_store_api": "/snapsecret/apigateway"
      "frontend_domain": "snapsecret.example.com",
      "frontend_acm_arn": "arn:aws:acm:us-east-1:1234567890:certificate/my-certificate-id",
      "api_domain": "api.snapsecret.example.com",
      "api_acm_arn": "arn:aws:acm:ap-southeast-2:1234567890:certificate/my-certificate-id",
  }
}
```

Otherwise, you can include them during the `cdk deploy` command if you prefer:

```
sktan ➜ ~/repos/sktan/snapsecret/cdk (master ✗) $ pipenv run cdk deploy -c frontend_domain=snapsecret.example.com -c api_domain=api.snapsecret.example.com -c "api_acm_arn=arn:aws:acm:ap-southeast-2:1234567890:certificate/my-certificate-id" -c "frontend_acm_arn=arn:aws:acm:us-east-1:1234567890:certificate/my-certificate-id" -e snapsecret-backend
sktan ➜ ~/repos/sktan/snapsecret/cdk (master ✗) $ pipenv run cdk deploy -c frontend_domain=snapsecret.example.com -c api_domain=api.snapsecret.example.com -c "api_acm_arn=arn:aws:acm:ap-southeast-2:1234567890:certificate/my-certificate-id" -c "frontend_acm_arn=arn:aws:acm:us-east-1:1234567890:certificate/my-certificate-id" -e snapsecret-frontend
```

## Development

Requirements:
- Black (for Python formatting)
- Eslint (for Nodejs formatting)
- boto3 (for testing the lambda function)
- boto3-stubs (optional, but for boto3 type hinting)

You are able to run a local development environment by deploying the backend services to AWS, and adding the API gateway the `frontend/.env` file (copy the contents from `frontend/.env.example`).

Once you have deployed the backend, you can run the `npm run dev` command to start the frontend development server.

You will be able to find the backend lambda function source in the `src` directory.
