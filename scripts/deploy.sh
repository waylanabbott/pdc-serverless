#!/usr/bin/env bash
# One-command deploy: infrastructure (SAM) -> site config -> seed DynamoDB -> upload site -> CloudFront invalidation.
# Used locally AND by the GitHub Actions pipeline.
set -euo pipefail
cd "$(dirname "$0")/.."
STACK=pdc-serverless
REGION=${AWS_REGION:-us-east-1}

echo "==> sam deploy"
sam deploy --no-progressbar

out() { aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
          --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
API_URL=$(out ApiUrl); CF_DOMAIN=$(out CloudFrontDomain); DIST_ID=$(out DistributionId)
BUCKET=$(out SiteBucketName); TABLE=$(out TableName)

echo "==> writing site/config.js"
printf 'window.PDC_CONFIG = { apiUrl: "%s" };\n' "$API_URL" > site/config.js

echo "==> seeding DynamoDB ($TABLE)"
python3 scripts/build_seed.py "$TABLE" "https://$CF_DOMAIN" .seed
for f in .seed/batch-*.json; do
  aws dynamodb batch-write-item --region "$REGION" --request-items "file://$f" --output text >/dev/null
done

echo "==> uploading site to s3://$BUCKET"
aws s3 sync site/images "s3://$BUCKET/images" --region "$REGION" --cache-control "public,max-age=86400" --delete
aws s3 sync site "s3://$BUCKET" --region "$REGION" --exclude "images/*" --cache-control "no-cache" --delete

echo "==> invalidating CloudFront"
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" --query Invalidation.Id --output text

echo
echo "Live site: https://$CF_DOMAIN/index.html?store=provo"
echo "API:       $API_URL/items?store=provo"
