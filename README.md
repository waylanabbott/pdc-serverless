# Paradise Donut Company: Serverless Store Menu

IS 531 Serverless Project · Waylan Abbott

A web page that shows one store's donut menu at a time, fully serverless:

```
Browser ──HTTPS──▶ CloudFront ──OAC──▶ S3 (index.html, config.js, images/)
   │
   └──fetch──▶ API Gateway (HTTP API)  GET /items?store=kyoto , GET /stores
                    │
                    ▼
               Lambda (Python 3.12) ──Query──▶ DynamoDB (pdc-serverless-menu)
```

## Data model (single table)

| PK | SK | What |
|---|---|---|
| `STORE#kyoto` | `META` | store name, city, hours, currency |
| `STORE#kyoto` | `ITEM#glazed` | name, price, rating, calories, imageUrl |
| `STORES` | `STORE#kyoto` | one row per store, for the dropdown |

Loading a store = `Query PK = "STORE#<id>"`. Listing stores = `Query PK = "STORES"`. No Scans.
An item sold at two stores is stored once under each store's partition (own price/currency).

## Repo layout

| Path | Purpose |
|---|---|
| `template.yaml` | SAM / CloudFormation: DynamoDB, Lambda, HTTP API, S3, CloudFront + OAC, CloudWatch alarm |
| `src/get_items/app.py` | Lambda (Python) |
| `site/` | Front end uploaded to S3 |
| `data/menu.json` | Stores, catalog, per-store menus (seed data) |
| `scripts/deploy.sh` | One-command deploy (used locally and by CI) |
| `pipeline/github-oidc-role.yaml` | One-time IAM role for GitHub Actions |
| `.github/workflows/deploy.yml` | CI/CD pipeline: test → sam deploy → seed → upload → invalidate |

## Deploy

Prereqs: AWS CLI v2 configured (`aws sts get-caller-identity` works), SAM CLI, Python 3.

```bash
./scripts/deploy.sh
```

Prints the live site URL and the API URL.

## Tear down (after grades are posted)

```bash
aws s3 rm s3://$(aws cloudformation describe-stacks --stack-name pdc-serverless --query "Stacks[0].Outputs[?OutputKey=='SiteBucketName'].OutputValue" --output text) --recursive
sam delete --stack-name pdc-serverless --no-prompts
```
