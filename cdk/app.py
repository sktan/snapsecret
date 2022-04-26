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
frontend = FrontendStack(app, "snapsecret-frontend", env=cdk_env)

# Ensure that if we do a `cdk deploy --all` then it will deploy the backend one first
# This is because the frontend asset build requires references from the backend stack
# As we can't pass these references via CDK code, we store them in parameter store
frontend.add_dependency(backend)

app.synth()
