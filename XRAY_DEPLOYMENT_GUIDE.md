# X-Ray Tracing Deployment Guide

## Overview
This guide covers the implementation of AWS X-Ray tracing for the People Registry API to provide comprehensive observability and performance monitoring.

## What Was Implemented

### 1. Infrastructure Changes (CDK)
- **Location**: `registry-infrastructure/people_register_infrastructure/people_register_infrastructure_stack.py`
- **Changes**:
  - Added `tracing=_lambda.Tracing.ACTIVE` to all Lambda functions
  - Added `_X_AMZN_TRACE_ID` environment variable to Lambda functions
  - Enabled X-Ray tracing for:
    - Authentication Lambda (`AuthFunction`)
    - API Lambda (`PeopleApiFunction`) 
    - Router Lambda (`RouterFunction`)

### 2. Application Code Changes

#### X-Ray Configuration Module
- **Location**: `registry-api/src/utils/xray_config.py`
- **Features**:
  - Automatic X-Ray SDK initialization
  - Environment detection (Lambda vs local)
  - Safe fallback when X-Ray is not available
  - Helper functions for annotations, metadata, and subsegments

#### Lambda Handler Updates
- **Location**: `registry-api/main.py`
- **Changes**:
  - Wrapped Lambda handler with X-Ray tracing
  - Added request/response metadata
  - Added error tracking annotations

#### DynamoDB Service Tracing
- **Location**: `registry-api/src/services/defensive_dynamodb_service.py`
- **Changes**:
  - Added X-Ray subsegments for database operations
  - Added annotations for filtering (operation type, table name)
  - Added metadata for detailed information (person_id, email, errors)
  - Wrapped key methods: `create_person`, `get_person`

### 3. Dependencies
- **Added**: `aws-xray-sdk==2.14.0` to both `requirements.txt` and `requirements-lambda.txt`

## Deployment Steps

### Step 1: Deploy Infrastructure Changes
```bash
cd registry-infrastructure
cdk diff  # Review changes
cdk deploy  # Deploy X-Ray tracing configuration
```

### Step 2: Deploy API Code
The API code deployment depends on your current deployment method:

#### Option A: Container Deployment (ECR)
```bash
cd registry-api
# Build and push container with X-Ray SDK
docker build -f Dockerfile.lambda -t registry-api-lambda .
# Tag and push to ECR (follow your existing process)
```

#### Option B: ZIP Deployment
```bash
cd registry-api
# Install dependencies including X-Ray SDK
pip install -r requirements-lambda.txt -t ./package/
# Package and deploy (follow your existing process)
```

### Step 3: Verify Deployment
1. **Check Lambda Configuration**:
   - Go to AWS Lambda Console
   - Verify "Active tracing" is enabled for all functions
   - Check environment variables include `_X_AMZN_TRACE_ID`

2. **Test API Endpoints**:
   ```bash
   # Test a few API calls to generate traces
   curl -X GET "https://your-api-gateway-url/api/v2/people"
   curl -X POST "https://your-api-gateway-url/api/v2/people" -d '{"first_name":"Test","last_name":"User","email":"test@example.com"}'
   ```

3. **Check X-Ray Console**:
   - Go to AWS X-Ray Console
   - View Service Map
   - Check Traces for recent requests
   - Verify subsegments for DynamoDB operations

## X-Ray Features Implemented

### Annotations (Indexed, Filterable)
- `service`: "people-registry-api"
- `version`: "v2"
- `operation`: Database operation type
- `table`: DynamoDB table name
- `error`: Error status
- `found`: Whether record was found

### Metadata (Detailed Information)
- `lambda.event_type`: HTTP method
- `lambda.path`: Request path
- `lambda.request_id`: AWS request ID
- `lambda.status_code`: Response status
- `dynamodb.person_id`: Person ID for operations
- `dynamodb.email`: Person email
- `dynamodb.error_code`: DynamoDB error codes

### Subsegments
- `create_person`: Person creation operations
- `get_person`: Person retrieval operations
- `dynamodb_put_item`: DynamoDB put operations
- `dynamodb_get_item`: DynamoDB get operations

## Monitoring and Alerting

### Key Metrics to Monitor
1. **Response Time**: Lambda duration and DynamoDB operation latency
2. **Error Rate**: Failed requests and database errors
3. **Throughput**: Requests per second
4. **Cold Starts**: Lambda initialization time

### Recommended CloudWatch Alarms
```bash
# High error rate
aws cloudwatch put-metric-alarm \
  --alarm-name "PeopleAPI-HighErrorRate" \
  --alarm-description "High error rate in People API" \
  --metric-name ErrorRate \
  --namespace AWS/X-Ray \
  --statistic Average \
  --period 300 \
  --threshold 5.0 \
  --comparison-operator GreaterThanThreshold

# High response time
aws cloudwatch put-metric-alarm \
  --alarm-name "PeopleAPI-HighLatency" \
  --alarm-description "High latency in People API" \
  --metric-name ResponseTime \
  --namespace AWS/X-Ray \
  --statistic Average \
  --period 300 \
  --threshold 2.0 \
  --comparison-operator GreaterThanThreshold
```

## Troubleshooting

### Common Issues

1. **No Traces Appearing**:
   - Check Lambda function has "Active tracing" enabled
   - Verify X-Ray SDK is installed in deployment package
   - Check CloudWatch logs for X-Ray errors

2. **Incomplete Traces**:
   - Verify all services have X-Ray tracing enabled
   - Check IAM permissions for X-Ray
   - Ensure subsegments are properly closed

3. **Performance Impact**:
   - X-Ray adds minimal overhead (~1-2ms per request)
   - Monitor Lambda duration metrics
   - Adjust sampling rate if needed

### IAM Permissions
The Lambda execution role needs these permissions (should be automatic with CDK):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

## Cost Considerations
- X-Ray charges $5.00 per 1 million traces recorded
- First 100,000 traces per month are free
- Typical API with 1000 requests/day = ~30,000 traces/month (within free tier)

## Next Steps
1. Deploy the changes to a development environment first
2. Test thoroughly and verify traces appear correctly
3. Set up CloudWatch dashboards for key metrics
4. Configure alerts for error rates and performance
5. Deploy to production during a maintenance window

## Testing X-Ray Locally
Run the included test script to verify configuration:
```bash
cd registry-api
python test_xray.py
```

This will verify that X-Ray imports work correctly and gracefully handles non-Lambda environments.
