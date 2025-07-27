# People Register API

A serverless REST API for people registration built with Python, FastAPI, and AWS Lambda.

## Architecture

- **Runtime**: Python 3.11
- **Framework**: FastAPI with Pydantic for data validation
- **Database**: Amazon DynamoDB
- **Deployment**: AWS Lambda with API Gateway
- **CORS**: Enabled for cross-origin requests

## Features

- ✅ **Full CRUD Operations**: Create, read, update, delete people
- ✅ **Data Validation**: Comprehensive input validation with Pydantic
- ✅ **Error Handling**: Proper HTTP status codes and error messages
- ✅ **CORS Support**: Cross-origin resource sharing enabled
- ✅ **Serverless**: Pay-per-use AWS Lambda deployment
- ✅ **Type Safety**: Full TypeScript-like type hints in Python

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check endpoint |
| GET | `/people` | List all registered people |
| POST | `/people` | Create a new person |
| GET | `/people/{id}` | Get person by ID |
| PUT | `/people/{id}` | Update person by ID |
| DELETE | `/people/{id}` | Delete person by ID |

## Data Model

```json
{
  "id": "uuid",
  "firstName": "string",
  "lastName": "string", 
  "email": "string",
  "phone": "string",
  "dateOfBirth": "YYYY-MM-DD",
  "address": {
    "street": "string",
    "city": "string",
    "state": "string",
    "zipCode": "string",
    "country": "string"
  },
  "createdAt": "ISO 8601 timestamp",
  "updatedAt": "ISO 8601 timestamp"
}
```

## Project Structure

```
src/
├── handlers/
│   └── people_handler.py    # Lambda function handlers
├── models/
│   └── person.py           # Pydantic data models
└── services/
    └── dynamodb_service.py # DynamoDB operations
tests/
└── test_person_model.py    # Unit tests
requirements.txt            # Python dependencies
```

## Dependencies

- **boto3**: AWS SDK for Python
- **pydantic**: Data validation and settings management
- **fastapi**: Modern web framework for building APIs
- **mangum**: ASGI adapter for AWS Lambda
- **python-json-logger**: Structured logging

## Development

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Local development with SAM (optional)
sam local start-api
```

### Testing

The API includes comprehensive unit tests for:
- Data model validation
- CRUD operations
- Error handling
- Input sanitization

## Deployment

This API is designed to be deployed as AWS Lambda functions with:

- **API Gateway**: HTTP API routing
- **DynamoDB**: Data persistence
- **CloudWatch**: Logging and monitoring
- **IAM**: Least privilege access control

### Environment Variables

- `PEOPLE_TABLE_NAME`: DynamoDB table name for storing people data

## Example Usage

### Create a Person

```bash
curl -X POST https://your-api-url/people \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "John",
    "lastName": "Doe", 
    "email": "john.doe@example.com",
    "phone": "+1-555-123-4567",
    "dateOfBirth": "1990-01-01",
    "address": {
      "street": "123 Main St",
      "city": "Anytown", 
      "state": "CA",
      "zipCode": "12345",
      "country": "USA"
    }
  }'
```

### List All People

```bash
curl https://your-api-url/people
```

### Get Person by ID

```bash
curl https://your-api-url/people/{person-id}
```

## Security

- Input validation with Pydantic models
- CORS headers properly configured
- Error messages don't expose sensitive information
- IAM roles follow least privilege principle

## Monitoring

- CloudWatch Logs for request/response logging
- Structured JSON logging for better observability
- Health check endpoint for monitoring systems

## Contributing

1. Follow existing code patterns and structure
2. Add tests for new features
3. Update documentation for API changes
4. Use type hints throughout the codebase
