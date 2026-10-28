# Atlas — Cloud-Native Enterprise RAG Platform

**AWS-first reference implementation** of a document-grounded knowledge assistant. Not a production certification or a claim of error-free deployment. The app requires a real AWS account, Bedrock model access, regional availability, and billable services.

## Architecture

React/Vite web app → Amazon Cognito → API Gateway HTTP API (JWT) → Lambda REST API → Amazon Bedrock (Titan embeddings + Claude) → Amazon OpenSearch Serverless (vector retrieval). Document upload: presigned S3 PUT → S3 event → SQS with DLQ → Lambda ingestion worker → DynamoDB metadata + OpenSearch vectors.

## Prerequisites

* AWS account and IAM permissions for CDK deployment; AWS CLI configured.
* AWS CDK bootstrap completed in chosen region.
* Node.js 20+, Python 3.11, npm, Docker running (CDK Python bundling uses Docker).
* Bedrock model availability/permissions for `amazon.titan-embed-text-v2:0` and chosen chat model in your AWS region. Model IDs vary by region; some require inference profiles.
* OpenSearch Serverless quotas and billing capacity. **This is NOT a free-tier project.** Create a cost budget and destroy resources when done.

## Deployment

```bash
aws sts get-caller-identity
npm install -g aws-cdk
cd infra
npm install
cdk bootstrap
cdk deploy
```

Copy `ApiUrl`, `UserPoolId`, `ClientId`, `Region` from CDK outputs.

Create a test user (use an email you control):

```bash
aws cognito-idp admin-create-user --user-pool-id YOUR\_POOL\_ID --username you@example.com --temporary-password 'ChangeMe123!'
aws cognito-idp admin-set-user-password --user-pool-id YOUR\_POOL\_ID --username you@example.com --password 'YOUR\_STRONG\_PASSWORD' --permanent
```

Configure frontend:

```bash
cd ../frontend
cp .env.example .env.local
# Edit VITE\_API\_URL, VITE\_USER\_POOL\_ID, VITE\_CLIENT\_ID
npm install
npm run dev
```

Visit `http://localhost:5173`, log in, upload `sample\_policy.txt`, refresh until READY, then ask: `When must incidents be reported?`

## Deploy web UI to cloud

Build `npm run build`, then host `frontend/dist` on AWS Amplify Hosting (connect GitHub) or S3 + CloudFront with HTTPS. Update CORS allowed origins in `infra/app.js` to your deployed web origin and redeploy. Never publish Cognito client secrets (this app uses a public client).

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q backend
```

These are unit tests; full integration tests require deployed AWS infrastructure and access to Bedrock and OpenSearch.

## Costs \& teardown

OpenSearch Serverless, Bedrock usage, Lambda, S3, SQS, CloudWatch and other resources may incur charges even when idle. OpenSearch Serverless is often the largest fixed cost. Use AWS Budgets alerts. `cdk destroy` does **not** delete retained S3 buckets, DynamoDB tables or retained Cognito pools; remove them separately after backing up and confirming they are no longer needed. OpenSearch collection may also require policy cleanup.

## 

