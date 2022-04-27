#!/usr/bin/env python3
import os
import aws_cdk as cdk

from snapsecret.backend_stack import BackendStack
from snapsecret.frontend_stack import FrontendStack

cdk_env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)

app = cdk.App()

backend = BackendStack(app, "snapsecret-backend", env=cdk_env)
frontend = FrontendStack(
    app, "snapsecret-frontend", backend_domain=backend.backend_domain, env=cdk_env
)

app.synth()
