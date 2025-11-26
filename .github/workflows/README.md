# GitHub Actions Workflows

## Setup Instructions

### 1. Configure AWS OIDC Provider

Create an OIDC provider in AWS IAM:

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 2. Create IAM Role for GitHub Actions

Create a role with this trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::142728997126:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:awscbba/registry-api:*"
        }
      }
    }
  ]
}
```

Attach these policies to the role:
- ECR push/pull permissions
- Lambda update function code permissions

### 3. Add GitHub Secret

Add the role ARN as a repository secret:
- Name: `AWS_ROLE_ARN`
- Value: `arn:aws:iam::142728997126:role/GitHubActionsRole`

### 4. Workflows

- **deploy-api.yml**: Deploys to Lambda on push to main
- **pr-validation.yml**: Validates PRs with tests and linting

## Testing

Test the deployment workflow manually:
```bash
gh workflow run deploy-api.yml
```
