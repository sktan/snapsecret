# CDK stack for Snap Secret

This project builds the CDK stack required to operate Snap Secret in AWS. Resources that are created in this stack includes:

- CloudFront Distribution
- 2x S3 Buckets to store the assets + assets bundle
- DynamoDB
- API Gateway
- 1x Lambda Function (to handle GET and PUT requests to the /secret endpoint)
- KMS (we will be using the dynamodb default kms key)
