import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Fn,
    Stack,
    aws_apigateway as apigw,
    aws_certificatemanager as acm,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_ssm as ssm,
    aws_iam as iam,
)
from constructs import Construct


class BackendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        paramstore_path = None
        if not (paramstore_path := self.node.try_get_context("parameter_store_api")):
            paramstore_path = "/snapsecret/apigateway"

        api_domain = self.node.try_get_context("api_domain")
        api_acm_arn = self.node.try_get_context("api_acm_arn")
        if (api_domain or api_acm_arn) and not (api_domain and api_acm_arn):
            raise Exception(
                "both `api_domain` and `api_acm_arn` context values are required"
            )

        # if a domain CDK context couldn't be resolved, allow all origins for CORS
        # This isn't secure, but it allows for testing via localhost / cloudfront
        snapsecret_origins = list()
        if domain := self.node.try_get_context("frontend_domain"):
            snapsecret_origins.append(f"https://{domain}")
        else:
            snapsecret_origins = apigw.Cors.ALL_ORIGINS

        if dev_url := self.node.try_get_context("dev_url"):
            snapsecret_origins.append(dev_url)

        table = dynamodb.Table(
            self,
            id="snapsecret_table",
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            time_to_live_attribute="expires_at",
            partition_key=dynamodb.Attribute(
                name="secret_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        bucket = s3.Bucket(
            self,
            "secret_file_bucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(1),
                    abort_incomplete_multipart_upload_after=Duration.days(1),
                )
            ],
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.DELETE,
                    ],
                    allowed_origins=snapsecret_origins,
                )
            ],
        )

        backend_lambda = lambda_.Function(
            self,
            id="snapsecret_lambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../src"),
            handler="snapsecret.handler",
            environment={
                "SECRETS_TABLE": table.table_name,
                "SECRETS_BUCKET": bucket.bucket_name,
                "CORS_ORIGINS": ",".join(snapsecret_origins),
            },
        )

        # Configure Lambda permissions
        table.grant_read_write_data(backend_lambda)
        backend_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:DeleteObject",
                ],
                effect=iam.Effect.ALLOW,
                resources=[bucket.arn_for_objects("*")],
            )
        )

        # Configure API gateway with /secret and /secret/:secrets_id endpoints
        api = apigw.RestApi(
            self,
            id="snapsecret_api",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=snapsecret_origins,
                allow_methods=["GET", "PUT"],
            ),
        )
        if api_domain:
            api.add_domain_name(
                id="snapsecret_api_domain",
                domain_name=api_domain,
                certificate=acm.Certificate.from_certificate_arn(
                    self,
                    id="snapsecret_api_domain_certificate",
                    certificate_arn=api_acm_arn,
                ),
                security_policy=apigw.SecurityPolicy.TLS_1_2,
            )

        cdk.CfnOutput(
            self,
            id="snapsecret_api_domain",
            value=api_domain
            if api_domain is not None
            else Fn.split("/", api.url, 4)[2],
        )

        cdk.CfnOutput(
            self,
            id="snapsecret_api_url",
            value=api.url if not api_domain else f"https://{api_domain}",
        )

        secret_ep = api.root.add_resource("secret")
        secret_ep.add_method("PUT", apigw.LambdaIntegration(backend_lambda))

        secret_get_ep = secret_ep.add_resource("{secret_id}")
        secret_get_ep.add_method("GET", apigw.LambdaIntegration(backend_lambda))

        file_ep = api.root.add_resource("file")
        file_ep_new = file_ep.add_resource("new")
        file_ep_new.add_method("GET", apigw.LambdaIntegration(backend_lambda))

        # store the API endpoint into a parameter store value
        ssm.CfnParameter(
            self,
            id="snapsecret_api_url_param",
            name=f"{paramstore_path}/url",
            type="String",
            value=api.url if not api_domain else f"https://{api_domain}",
        )

        ssm.CfnParameter(
            self,
            id="snapsecret_api_domain_param",
            name=f"{paramstore_path}/domain",
            type="String",
            value=api_domain
            if api_domain is not None
            else Fn.split("/", api.url, 4)[2],
        )
