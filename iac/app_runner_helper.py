from aws_cdk import (
    aws_apprunner as apprunner,
    aws_ec2 as ec2,
    aws_iam as iam,
    core,
)


class StreamlitAppRunnerStack(core.Stack):
    # Default values for overridable properties
    DEFAULT_VPC_DESCRIPTION = "VPC for App Runner service"
    DEFAULT_SECURITY_GROUP_DESCRIPTION = "Allow access to App Runner service from specific IP ranges"
    DEFAULT_APP_RUNNER_ROLE_DESCRIPTION = "IAM Role for App Runner tasks"
    DEFAULT_IMAGE_REPOSITORY_TYPE = "ECR_PUBLIC"
    DEFAULT_CPU = "1024"
    DEFAULT_MEMORY = "2048"
    DEFAULT_ENV_VAR_NAME = "CONFIG_PATH"
    DEFAULT_INGRESS_PORT = 443
    DEFAULT_SECRETS_POLICY_NAME = "SecretsManagerReadWrite"
    DEFAULT_SERVICE_NAME = "StreamlitAppRunnerService"

    def __init__(
        self,
        scope: core.Construct,
        id: str,
        *,
        container_image: str,
        config_path_env_var: str,
        assumed_role_arn: str = None,  # Optional: Provide an existing role or create one
        allowed_ip_ranges: list = None,  # Optional: Provide IP ranges for ingress
        vpc_id: str = None,  # Optional: Provide an existing VPC ID or create one
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        # Create or use an existing VPC
        if vpc_id:
            vpc = ec2.Vpc.from_lookup(self, "AppRunnerVPC", vpc_id=vpc_id)
        else:
            vpc = ec2.Vpc(
                self,
                "AppRunnerVpc",
                max_azs=2,
                nat_gateways=1,
                description=self.DEFAULT_VPC_DESCRIPTION,
            )

        # Create a security group
        security_group = ec2.SecurityGroup(
            self,
            "AppRunnerSecurityGroup",
            vpc=vpc,
            description=self.DEFAULT_SECURITY_GROUP_DESCRIPTION,
            allow_all_outbound=True,
        )

        # Restrict inbound traffic if allowed_ip_ranges are provided
        if allowed_ip_ranges:
            for ip_range in allowed_ip_ranges:
                security_group.add_ingress_rule(
                    peer=ec2.Peer.ipv4(ip_range),
                    connection=ec2.Port.tcp(self.DEFAULT_INGRESS_PORT),
                    description=f"Allow access from {ip_range}",
                )

        # Create or use an existing IAM role
        if assumed_role_arn:
            task_role = iam.Role.from_role_arn(self, "AppRunnerTaskRole", assumed_role_arn)
        else:
            task_role = iam.Role(
                self,
                "AppRunnerDefaultRole",
                assumed_by=iam.ServicePrincipal("tasks.apprunner.amazonaws.com"),
                description=self.DEFAULT_APP_RUNNER_ROLE_DESCRIPTION,
            )
            # Attach a policy for reading secrets and other AWS resources
            task_role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name(self.DEFAULT_SECRETS_POLICY_NAME)
            )

        # Create the App Runner service
        service = apprunner.CfnService(
            self,
            self.DEFAULT_SERVICE_NAME,
            source_configuration=apprunner.CfnService.SourceConfigurationProperty(
                image_repository=apprunner.CfnService.ImageRepositoryProperty(
                    image_identifier=container_image,
                    image_repository_type=self.DEFAULT_IMAGE_REPOSITORY_TYPE,
                ),
                authentication_configuration=apprunner.CfnService.AuthenticationConfigurationProperty(
                    access_role_arn=task_role.role_arn
                ),
            ),
            network_configuration=apprunner.CfnService.NetworkConfigurationProperty(
                egress_configuration=apprunner.CfnService.EgressConfigurationProperty(
                    egress_type="VPC",
                    vpc_connector_name=f"{id}-VPCConnector",
                )
            ),
            instance_configuration=apprunner.CfnService.InstanceConfigurationProperty(
                cpu=self.DEFAULT_CPU,
                memory=self.DEFAULT_MEMORY,
                environment_variables={
                    self.DEFAULT_ENV_VAR_NAME: config_path_env_var,
                },
            ),
        )

        # Output the App Runner URL
        core.CfnOutput(
            self,
            "AppRunnerServiceUrl",
            value=service.attr_service_url,
            description="URL of the deployed Streamlit App",
        )
