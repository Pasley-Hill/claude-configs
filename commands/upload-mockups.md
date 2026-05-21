# Upload Mockups

Sync HTML mockups to S3 for public hosting and invalidate CloudFront cache.

> **PROJECT-SPECIFIC: replace `{MOCKUPS_DIR}`, `{S3_BUCKET_PATH}`, `{AWS_PROFILE}`, `{CLOUDFRONT_DISTRIBUTION_ID}`, `{CACHE_INVALIDATION_PATH}`, and `{PUBLIC_MOCKUP_URL}` with project values.**

## Instructions

1. Run the following command to sync mockups:

```bash
aws s3 sync {MOCKUPS_DIR}/ s3://{S3_BUCKET_PATH}/ --profile {AWS_PROFILE}
```

2. Invalidate the CloudFront cache:

```bash
aws cloudfront create-invalidation --distribution-id {CLOUDFRONT_DISTRIBUTION_ID} --paths "{CACHE_INVALIDATION_PATH}" --profile {AWS_PROFILE}
```

3. Report the results to the user
4. Provide the URLs for any uploaded files at `{PUBLIC_MOCKUP_URL}`
