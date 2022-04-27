import aws_cdk as cdk
from aws_cdk import (
    # Duration,
    Stack,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigw,
    aws_ssm as ssm,
    aws_lambda as lambda_,
    aws_certificatemanager as acm,
)
from constructs import Construct


class BackendStack(Stack):
    backend_domain = None

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

        backend_lambda = lambda_.Function(
            self,
            id="snapsecret_lambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset("../src"),
            handler="snapsecret.handler",
            environment={
                "SECRETS_TABLE": table.table_name,
                "CORS_ORIGINS": ",".join(snapsecret_origins),
            },
        )

        # Configure Lambda permissions
        table.grant_read_write_data(backend_lambda)

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
            api_alias = api.add_domain_name(
                id="snapsecret_api_domain",
                domain_name=api_domain,
                certificate=acm.Certificate.from_certificate_arn(
                    self,
                    id="snapsecret_api_domain_certificate",
                    certificate_arn=api_acm_arn,
                ),
                security_policy=apigw.SecurityPolicy.TLS_1_2,
            )
            self.backend_domain = api_alias.domain_name

            cdk.CfnOutput(
                self,
                id="snapsecret_api_alias_domain",
                value=api_alias.domain_name_alias_domain_name,
            )
            cdk.CfnOutput(
                self,
                id="snapsecret_api_alias_url",
                value=f"https://{api_alias.domain_name}/",
            )
        else:
            self.backend_domain = api.domain_name

        secret_ep = api.root.add_resource("secret")
        secret_ep.add_method("PUT", apigw.LambdaIntegration(backend_lambda))

        secret_get_ep = secret_ep.add_resource("{secret_id}")
        secret_get_ep.add_method("GET", apigw.LambdaIntegration(backend_lambda))

        # store the API endpoint into a parameter store value
        ssm.CfnParameter(
            self,
            id="snapsecret_api_param",
            name=paramstore_path,
            type="String",
            value=api.url if not api_domain else f"https://{api_domain}",
        )
