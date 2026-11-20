#!/usr/bin/env bash
# One-time: IAM role for GitHub Actions (OIDC) + private GitHub repo + secret + first push.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO_NAME=${1:-pdc-serverless}
REGION=us-east-1

command -v gh >/dev/null || { echo "Install GitHub CLI first: brew install gh && gh auth login"; exit 1; }
gh auth status >/dev/null 2>&1 || gh auth login
OWNER=$(gh api user --jq .login)

if aws iam list-open-id-connect-providers --output text | grep -q token.actions.githubusercontent.com; then
  CREATE=false; echo "==> GitHub OIDC provider already exists (from SAM lab), reusing it"
else
  CREATE=true;  echo "==> Creating GitHub OIDC provider"
fi

echo "==> Deploying IAM deploy role for $OWNER/$REPO_NAME"
aws cloudformation deploy --region $REGION --stack-name pdc-serverless-github-role \
  --template-file pipeline/github-oidc-role.yaml --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides GitHubRepo="$OWNER/$REPO_NAME" CreateOidcProvider=$CREATE
ROLE_ARN=$(aws cloudformation describe-stacks --region $REGION --stack-name pdc-serverless-github-role \
  --query "Stacks[0].Outputs[?OutputKey=='DeployRoleArn'].OutputValue" --output text)

echo "==> Creating repo and pushing"
[ -d .git ] || git init -q -b main
git add -A
git commit -qm "Paradise Donut serverless menu: SAM template, Python Lambda, site, pipeline" || true
gh repo view "$OWNER/$REPO_NAME" >/dev/null 2>&1 || gh repo create "$REPO_NAME" --private --source . --remote origin
git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$OWNER/$REPO_NAME.git"
gh secret set AWS_DEPLOY_ROLE_ARN --repo "$OWNER/$REPO_NAME" --body "$ROLE_ARN"
git push -u origin main

echo
echo "Pipeline: https://github.com/$OWNER/$REPO_NAME/actions"
