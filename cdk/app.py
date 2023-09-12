#!/usr/bin/env python3
import os
import aws_cdk as cdk

from snapsecret.backend_stack import BackendStack
from snapsecret.frontend_stack import FrontendStack

backend_env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)

frontend_env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region="us-east-1",  # Cloudfront always deploys to N. Virginia
)

app = cdk.App()

backend = BackendStack(
    app,
    "snapsecret-backend",
    env=backend_env,
)

frontend = FrontendStack(
    app,
    "snapsecret-frontend",
    backend_region=backend_env.region,
    env=frontend_env,
)

app.synth()
