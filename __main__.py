import pulumi
import pulumi_aws as aws
import pulumi_synced_folder as synced_folder

# Import the program's configuration settings.
config = pulumi.Config()
path = config.get("path") or "./www"
index_document = config.get("indexDocument") or "index.html"
error_document = config.get("errorDocument") or "error.html"


# Create an kms for "Access_log_bucket" encryption 
Access_log_bucket = aws.s3.Bucket("AccesslogBucket", acl="log-delivery-write", server_side_encryption_configuration=aws.s3.BucketServerSideEncryptionConfigurationArgs(
        rule=aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
        apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
        sse_algorithm="AES256",
        ),
        ),),)

example_bucket_public_access_block = aws.s3.BucketPublicAccessBlock("BucketPublicAccessBlock",
    bucket=Access_log_bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True)        
# Create an S3 bucket and configure it as a website.
bucket = aws.s3.Bucket(
    "static-website-s3",
    loggings=[aws.s3.BucketLoggingArgs(
        target_bucket=Access_log_bucket.id,
        target_prefix="log/",
    )],
    acl="public-read",
    website=aws.s3.BucketWebsiteArgs(
        index_document=index_document,
        error_document=error_document,
    ),
)

bucket_policy_document = aws.iam.get_policy_document_output(statements=[aws.iam.GetPolicyDocumentStatementArgs(
    principals=[aws.iam.GetPolicyDocumentStatementPrincipalArgs(
        type="*",
        identifiers=["*"],
    )],
    actions=[
        "s3:GetObject"
    ],
    resources=[
        bucket.arn.apply(lambda arn: f"{arn}/*"),
    ],
)])
bucket_policy = aws.s3.BucketPolicy("AllowStaticWebsiteAccess",
    bucket=bucket.id,
    policy=bucket_policy_document.json)

# Use a synced folder to manage the files of the website.
bucket_folder = synced_folder.S3BucketFolder(
    "bucket-folder", path=path, bucket_name=bucket.bucket, acl="public-read"
)



# Create a CloudFront CDN to distribute and cache the website.

cdn = aws.cloudfront.Distribution(
    "cdn",
    enabled=True,
    origins=[
        aws.cloudfront.DistributionOriginArgs(
            origin_id=bucket.arn,
            domain_name=bucket.website_endpoint,
            custom_origin_config=aws.cloudfront.DistributionOriginCustomOriginConfigArgs(
                origin_protocol_policy="http-only",
                http_port=80,
                https_port=443,
                origin_ssl_protocols=["TLSv1.2"],
               ),
        ),
 
    ],

    default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
        target_origin_id=bucket.arn,
        viewer_protocol_policy="redirect-to-https",
        allowed_methods=[
            "GET",
            "HEAD",
            "OPTIONS",
        ],
        cached_methods=[
            "GET",
            "HEAD",
            "OPTIONS",
        ],
        default_ttl=600,
        max_ttl=600,
        min_ttl=600,
        forwarded_values=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesArgs(
            query_string=True,
            cookies=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesCookiesArgs(
                forward="all",
            ),
        ),
    ),
    price_class="PriceClass_100",
    custom_error_responses=[
        aws.cloudfront.DistributionCustomErrorResponseArgs(
            error_code=404,
            response_code=404,
            response_page_path=f"/{error_document}",
        )
    ],
    restrictions=aws.cloudfront.DistributionRestrictionsArgs(
        geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
            restriction_type="none",
        ),
    ),
    viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(
        cloudfront_default_certificate=True,
    ),

)



user_updates = aws.sns.Topic("topic",policy=bucket.arn.apply(lambda arn: f"""{{
    "Version":"2012-10-17",
    "Statement":[{{
        "Effect": "Allow",
        "Principal": {{ "Service": "s3.amazonaws.com" }},
        "Action": "sns:Publish",
        "Resource": "arn:aws:sns:*:*:topic-*",
        "Condition":{{
            "ArnLike":{{"aws:SourceArn":"{arn}"}}
        }}
    }}]
}}
"""))
bucket_notification = aws.s3.BucketNotification("bucketNotification",opts=pulumi.ResourceOptions(depends_on=[user_updates]),
    bucket=bucket.id,
    topics=[aws.s3.BucketNotificationTopicArgs(
        topic_arn=user_updates.arn,
        events=["s3:ObjectCreated:*","s3:ObjectRemoved:*","s3:ObjectAcl:Put"]
    )])

sns_topic_topic_subscription = aws.sns.TopicSubscription("user-updates-subscribe",
    topic=user_updates.arn,
    protocol="email",
    endpoint="ester.hatchuel@gmail.com"
)




# Export the URLs and hostnames of the bucket and distribution.
pulumi.export("originURL", pulumi.Output.concat("http://", bucket.website_endpoint))
pulumi.export("originHostname", bucket.website_endpoint)
pulumi.export("cdnURL", pulumi.Output.concat("https://", cdn.domain_name))
pulumi.export("cdnHostname", cdn.domain_name)
