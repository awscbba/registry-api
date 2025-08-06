# Subscription Email Notifications Implementation

## Overview

This document describes the implementation of email notifications for subscription approval/rejection workflow, addressing the issue where users were not receiving email notifications when their subscription status changed.

## Problem Statement

Based on the conversation summary, users reported that the subscription approval workflow was not sending email notifications to users when their subscription status changed from "pending" to "active" (approved) or "inactive" (rejected).

## Solution Implementation

### 1. Email Types Added

Added new email types to support subscription notifications:

```python
# In src/models/email.py
class EmailType(str, Enum):
    # ... existing types ...
    SUBSCRIPTION_APPROVED = "subscription_approved"
    SUBSCRIPTION_REJECTED = "subscription_rejected"
```

### 2. Email Service Methods

Added two new methods to the `EmailService` class:

#### `send_subscription_approved_email()`
- Sends a professional, branded approval email
- Includes project details and next steps
- Provides dashboard access link
- Uses AWS User Group Cochabamba branding

#### `send_subscription_rejected_email()`
- Sends a respectful rejection email
- Includes rejection reason if provided
- Offers alternative actions (contact support, apply to other projects)
- Maintains professional tone

### 3. API Integration

Modified the subscription update endpoint (`PUT /v2/projects/{project_id}/subscribers/{subscription_id}`) to automatically send email notifications when subscription status changes:

```python
# In src/handlers/versioned_api_handler.py
@v2_router.put("/projects/{project_id}/subscribers/{subscription_id}")
async def update_project_subscription_v2(project_id: str, subscription_id: str, update_data: dict):
    # ... existing logic ...
    
    # Send email notification if status changed to approved or rejected
    if new_status and new_status != original_status:
        if new_status == "active":
            # Send approval email
        elif new_status == "inactive":
            # Send rejection email
```

### 4. Error Handling

- Email sending errors are logged but don't fail the subscription update
- Graceful fallback if person details are not found
- Proper error logging for debugging

### 5. Email Templates

#### Approval Email Features:
- Congratulatory header with gradient background
- Project details in a highlighted box
- Clear next steps and action items
- Dashboard access button
- Professional footer with AWS User Group branding

#### Rejection Email Features:
- Professional and respectful tone
- Clear explanation of status
- Rejection reason (if provided)
- Alternative actions and support contact
- Encouraging message for future opportunities

## Technical Details

### Email Content Structure

Both email types include:
- HTML and plain text versions
- Responsive design for mobile devices
- Professional styling with AWS User Group colors
- Proper Spanish localization
- Current year in footer

### Logging Integration

- Fixed logging service calls to use correct `LogCategory` values
- Email sending success/failure is properly logged
- Structured logging for debugging and monitoring

### Testing

Comprehensive test suite added (`test_subscription_email_notifications.py`):
- Tests for both approval and rejection emails
- Error handling verification
- Email content structure validation
- SES integration mocking
- All tests passing (6/6)

## Usage

### For Administrators

When updating a subscription status through the admin interface:

1. **To approve a subscription**: Set status to "active"
   - User receives approval email with project details
   - Email includes dashboard access link

2. **To reject a subscription**: Set status to "inactive"
   - User receives rejection email with reason (if provided in notes)
   - Email includes support contact information

### Email Triggers

Emails are automatically sent when:
- Subscription status changes from any status to "active" → Approval email
- Subscription status changes from any status to "inactive" → Rejection email
- No email is sent if status doesn't change or changes to other values

## Configuration

### Environment Variables

The email service uses these environment variables:
- `SES_FROM_EMAIL`: Sender email address (default: noreply@people-register.local)
- `FRONTEND_URL`: Frontend URL for dashboard links (default: https://d28z2il3z2vmpc.cloudfront.net)
- `AWS_REGION`: AWS region for SES (default: us-east-1)

### AWS SES Setup

Ensure AWS SES is properly configured:
- Sender email address is verified
- Appropriate sending limits are set
- IAM permissions for SES operations

## Monitoring and Debugging

### Logs to Monitor

1. **Successful email sending**:
   ```
   Email sent successfully to {email} for project {project_name}
   ```

2. **Email sending failures**:
   ```
   Failed to send subscription {status} email to {email}: {error_message}
   ```

3. **Email notification errors**:
   ```
   Error sending subscription status email notification: {error}
   ```

### Common Issues

1. **SES Configuration**: Verify sender email is verified in SES
2. **IAM Permissions**: Ensure API has SES sending permissions
3. **Network Issues**: Check AWS connectivity
4. **Email Content**: Verify template rendering doesn't fail

## Future Enhancements

Potential improvements for future versions:

1. **Email Templates**: Move to AWS SES templates for easier management
2. **Personalization**: Add more personalized content based on user profile
3. **Batch Notifications**: Support for bulk status updates with batch emails
4. **Email Preferences**: Allow users to configure notification preferences
5. **Rich Content**: Add project images and more detailed information

## Related Files

- `src/models/email.py` - Email type definitions
- `src/services/email_service.py` - Email service implementation
- `src/handlers/versioned_api_handler.py` - API endpoint integration
- `src/services/logging_service.py` - Logging service fixes
- `tests/test_subscription_email_notifications.py` - Test suite

## Verification

To verify the implementation works:

1. Run the test suite: `just test tests/test_subscription_email_notifications.py`
2. Run critical tests: `just test-critical`
3. Test in development environment by updating subscription status
4. Check logs for email sending confirmation

## Impact

This implementation resolves the reported issue where users were not receiving email notifications during the subscription approval workflow. Users will now receive:

- Clear, professional approval notifications with next steps
- Respectful rejection notifications with alternative actions
- Consistent branding and messaging
- Both HTML and plain text email versions
- Proper error handling and logging
