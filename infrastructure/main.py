#!/usr/bin/env python
from constructs import Construct
from cdktf import App, TerraformStack, TerraformOutput, TerraformVariable, S3Backend
from imports.aws import AwsProvider, AwsProviderAssumeRole
from imports.aws.iam import DataAwsIamRole, DataAwsIamPolicy
from imports.aws.apigatewayv2 import Apigatewayv2ApiConfig


class MyStack(TerraformStack):
    def __init__(self, scope: Construct, ns: str):
        super().__init__(scope, ns)

        # define resources here
        api_config = Apigatewayv2ApiConfig(name="repo_analysis_api_gw", protocol_type="HTTP")


app = App()
MyStack(app, "infrastructure")

app.synth()
