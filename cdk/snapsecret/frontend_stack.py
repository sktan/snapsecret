import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Stack,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_lambda as lambda_,
    aws_certificatemanager as acm,
)
import boto3
from constructs import Construct


class FrontendStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, backend_region: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        frontend_domain = self.node.try_get_context("frontend_domain")
        frontend_acm_arn = self.node.try_get_context("frontend_acm_arn")

        ssm_client = boto3.client("ssm", region_name=backend_region)

        if (frontend_domain or frontend_acm_arn) and not (
            frontend_domain and frontend_acm_arn
        ):
            raise Exception(
                "both `domain` and `frontend_acm_arn` context values are required"
            )

        paramstore_path = None
        if not (paramstore_path := self.node.try_get_context("parameter_store_api")):
            paramstore_path = "/snapsecret/apigateway"

        apigw_url = ""
        try:
            apigw_url = ssm_client.get_parameter(Name=f"{paramstore_path}/url")["Parameter"]["Value"]
        except Exception:
            # Set it to localhost temporarily, as the param hasn't been created until the backend
            # stack has been deployed. This is to fix the initial `cdk bootstrap` issue where
            # it attempts to synthesize the stacks
            apigw_url = "localhost"

        apigw_domain = ""
        try:
            apigw_domain = ssm_client.get_parameter(Name=f"{paramstore_path}/domain")["Parameter"]["Value"]
        except Exception:
            apigw_domain = "localhost"

        bucket = s3.Bucket(self, "snapsecret_frontend_bucket")
        cf_oai = cloudfront.OriginAccessIdentity(
            self,
            "snapsecret_originpolicy",
        )
        # Configure a cert if specified
        cf_cert = None
        if frontend_domain:
            cf_cert = acm.Certificate.from_certificate_arn(
                self,
                id="snapsecret_frontend_cert",
                certificate_arn=frontend_acm_arn,
            )

        cf_headers = cloudfront.ResponseHeadersPolicy(
            self,
            id="snapsecret_frontend_headers",
            custom_headers_behavior=cloudfront.ResponseCustomHeadersBehavior(
                custom_headers=[
                    cloudfront.ResponseCustomHeader(
                        override=True,
                        header="Feature-Policy",
                        value="layout-animations 'none'; unoptimized-images 'none'; oversized-images 'none'; sync-script 'none'; sync-xhr 'none'; unsized-media 'none';",
                    ),
                ]
            ),
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                    override=True,
                    referrer_policy=cloudfront.HeadersReferrerPolicy.NO_REFERRER,
                ),
                xss_protection=cloudfront.ResponseHeadersXSSProtection(
                    override=True, mode_block=True, protection=True
                ),
                content_type_options=cloudfront.ResponseHeadersContentTypeOptions(
                    override=True,
                ),
                content_security_policy=cloudfront.ResponseHeadersContentSecurityPolicy(
                    override=True,
                    content_security_policy=f"default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; connect-src https://{apigw_domain}/ data:",
                ),
                frame_options=cloudfront.ResponseHeadersFrameOptions(
                    override=True,
                    frame_option=cloudfront.HeadersFrameOption.DENY,
                ),
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    override=True,
                    access_control_max_age=Duration.days(365),
                    preload=True,
                ),
            ),
        )
        domain_names = None
        if frontend_domain:
            domain_names = [frontend_domain]
        cf_dist = cloudfront.Distribution(
            self,
            id="snapsecret_cloudfront",
            domain_names=domain_names,
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
            certificate=cf_cert,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    bucket=bucket,
                    origin_access_identity=cf_oai,
                ),
                response_headers_policy=cf_headers,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            error_responses=[
                cloudfront.ErrorResponse(
                    # When an item wasn't found, it returns a 403 not 404.
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                )
            ],
        )

        # Deploy the frontend assets to S3 and invalidate the CloudFront Cache
        setup_command = "&&".join(
            [
                "export npm_config_update_notifier=false",
                "export npm_config_cache=$(mktemp -d)",
                "npm install",
            ]
        )
        build_command = f'VITE_WEBAPI_ENDPOINT="{apigw_url}" npm run build && cp -au dist/* /asset-output'
        complete_build_command = setup_command + "&&" + build_command
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
                        image=lambda_.Runtime.NODEJS_18_X.bundling_image,
                        command=[
                            "bash",
                            "-xc",
                            complete_build_command,
                        ],
                    ),
                )
            ],
            destination_bucket=bucket,
        )

        cdk.CfnOutput(
            self,
            id="snapsecret_frontend_url",
            value=f"https://{cf_dist.domain_name}",
        )
