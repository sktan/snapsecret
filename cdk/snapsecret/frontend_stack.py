import aws_cdk as cdk
from aws_cdk import (
    # Duration,
    Stack,
    aws_cloudfront as cloudfront,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_lambda as lambda_,
    aws_certificatemanager as acm,
)
import boto3
from constructs import Construct


class FrontendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        frontend_domain = self.node.try_get_context("frontend_domain")
        frontend_acm_arn = self.node.try_get_context("frontend_acm_arn")

        if (frontend_domain or frontend_acm_arn) and not (
            frontend_domain and frontend_acm_arn
        ):
            raise Exception(
                "both `domain` and `frontend_acm_arn` context values are required"
            )

        paramstore_path = None
        if not (paramstore_path := self.node.try_get_context("parameter_store_api")):
            paramstore_path = "/snapsecret/apigateway"

        apigw_url = boto3.client("ssm").get_parameter(Name=paramstore_path)[
            "Parameter"
        ]["Value"]

        bucket = s3.Bucket(self, "snapsecret_frontend_bucket")
        cf_oai = cloudfront.OriginAccessIdentity(
            self,
            f"snapsecret_originpolicy",
        )
        # Configure a cert if specified
        cf_cert = None
        if frontend_domain:
            cf_cert = cloudfront.ViewerCertificate.from_acm_certificate(
                aliases=[frontend_domain],
                certificate=acm.Certificate.from_certificate_arn(
                    self,
                    id="snapsecret_frontend_cert",
                    certificate_arn=frontend_acm_arn,
                ),
                security_policy=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
            )

        cf_dist = cloudfront.CloudFrontWebDistribution(
            self,
            id="snapsecret_cloudfront",
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
            viewer_certificate=cf_cert,
            origin_configs=[
                cloudfront.SourceConfiguration(
                    behaviors=[cloudfront.Behavior(is_default_behavior=True)],
                    s3_origin_source=cloudfront.S3OriginConfig(
                        s3_bucket_source=bucket,
                        origin_access_identity=cf_oai,
                    ),
                )
            ],
            error_configurations=[
                cloudfront.CfnDistribution.CustomErrorResponseProperty(
                    # When an item wasn't found, it returns a 403 not 404.
                    error_code=403,
                    error_caching_min_ttl=0,
                    response_code=200,
                    response_page_path="/index.html",
                )
            ],
        )

        # Deploy the frontend assets to S3 and invalidate the CloudFront Cache
        build_command = f'npm install && VITE_WEBAPI_ENDPOINT="{apigw_url}" npm run build && cp -au dist/* /asset-output'
        s3_deployment.BucketDeployment(
            self,
            id="snapsecret_frontend_deploy",
            distribution=cf_dist,
            distribution_paths=["/*", "/"],
            sources=[
                # This is the directory where the frontend code lives
                # The bundling option will build the website frontend and use that
                # as the final source to deploy to S3
                s3_deployment.Source.asset(
                    "../frontend",
                    bundling=cdk.BundlingOptions(
                        # Using Node v14 as AWS doesn't support Node v16 yet
                        image=lambda_.Runtime.NODEJS_14_X.bundling_image,
                        command=[
                            "bash",
                            "-c",
                            build_command,
                        ],
                    ),
                )
            ],
            destination_bucket=bucket,
        )

        cdk.CfnOutput(
            self,
            id="snapsecret_frontend_url",
            value=f"https://{cf_dist.distribution_domain_name}",
        )
