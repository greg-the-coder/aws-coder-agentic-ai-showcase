"""FrontendStack — S3 static website + CloudFront distribution for the React SPA."""

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    Tags,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct

from lib.api_stack import ApiStack


class FrontendStack(Stack):
    """S3 + CloudFront for the React single-page application."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_stack: ApiStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("Project", "dc-invest-agent")

        # -----------------------------------------------------------------
        # S3 bucket for the SPA (private — served via CloudFront OAC)
        # -----------------------------------------------------------------
        self.website_bucket = s3.Bucket(
            self,
            "WebsiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # -----------------------------------------------------------------
        # CloudFront Distribution
        # -----------------------------------------------------------------
        self.distribution = cloudfront.Distribution(
            self,
            "SiteDistribution",
            comment="DC Investments Agent — MVP Demo",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    self.website_bucket,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
            ),
            # Route /v1/* and /mock/* to the API Gateway origin
            additional_behaviors={
                "/v1/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        f"{api_stack.api.rest_api_id}.execute-api.{self.region}.amazonaws.com",
                        origin_path="/prod",
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                ),
                "/mock/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        f"{api_stack.api.rest_api_id}.execute-api.{self.region}.amazonaws.com",
                        origin_path="/prod",
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                ),
            },
            default_root_object="index.html",
            # SPA: return index.html for 404s so client-side routing works
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
        )

        # -----------------------------------------------------------------
        # Deploy React build artifacts to S3
        # -----------------------------------------------------------------
        s3deploy.BucketDeployment(
            self,
            "DeploySite",
            sources=[s3deploy.Source.asset("../frontend/dist")],
            destination_bucket=self.website_bucket,
            distribution=self.distribution,
            distribution_paths=["/*"],
        )

        # -----------------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------------
        CfnOutput(
            self,
            "CloudFrontURL",
            value=f"https://{self.distribution.distribution_domain_name}",
            description="CloudFront URL — share this for the MVP demo",
            export_name="dcai-cloudfront-url",
        )
        CfnOutput(
            self,
            "DistributionId",
            value=self.distribution.distribution_id,
            export_name="dcai-distribution-id",
        )
        CfnOutput(
            self,
            "WebsiteBucketName",
            value=self.website_bucket.bucket_name,
            export_name="dcai-website-bucket",
        )
