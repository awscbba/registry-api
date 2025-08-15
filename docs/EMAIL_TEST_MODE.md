# Email Test Mode

## Problem
When running tests, especially password reset tests, the system was sending real emails to users, causing spam and confusion.

## Solution
Added `EMAIL_TEST_MODE` environment variable to disable actual email sending during tests while maintaining the same API behavior.

## Usage

### Environment Variable
Set `EMAIL_TEST_MODE=true` to enable test mode:

```bash
export EMAIL_TEST_MODE=true
```

### Justfile Commands
Use the new test commands that automatically enable test mode:

```bash
# Run all tests without sending emails
just test-no-emails

# Run critical tests without sending emails  
just test-critical-no-emails

# Run password-related tests without sending emails
just test-password-no-emails
```

### Manual Script
Use the provided script:

```bash
# Run tests with different options
./scripts/run_tests_no_emails.sh all        # All tests
./scripts/run_tests_no_emails.sh critical   # Critical tests
./scripts/run_tests_no_emails.sh password   # Password tests
./scripts/run_tests_no_emails.sh            # Default (critical tests)
```

## How It Works

When `EMAIL_TEST_MODE=true`:

1. **EmailService initialization**: Skips SES client creation
2. **Health checks**: Returns healthy status with test mode indicator
3. **Email sending**: Returns success response without actually sending emails
4. **Logging**: Logs what emails would be sent for debugging

## Benefits

- ✅ **No spam emails** during testing
- ✅ **Same API behavior** - tests still pass
- ✅ **Easy to enable/disable** with environment variable
- ✅ **Logging for debugging** - see what emails would be sent
- ✅ **Production safety** - defaults to false (real emails)

## Example Output

```
[email_service] INFO - EmailService running in TEST MODE - emails will not be sent
[email_service] INFO - TEST MODE: Would send password reset email to user@example.com (token: abc123...)
```

## Production Safety

- Test mode is **disabled by default**
- Only enabled when explicitly set: `EMAIL_TEST_MODE=true`
- Production deployments will send real emails unless explicitly configured otherwise
- Health check indicates test mode status

## Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `EMAIL_TEST_MODE` | `true`, `false`, `1`, `0`, `yes`, `no` | `false` | Enable/disable test mode |

## Integration with CI/CD

Add to your test pipeline:

```yaml
env:
  EMAIL_TEST_MODE: true
```

This prevents CI/CD runs from sending real emails to users.
