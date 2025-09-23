# InvestForge API

Serverless backend API for InvestForge using AWS Lambda and API Gateway.

## Architecture

- **Framework**: Serverless Framework
- **Runtime**: Python 3.9
- **Database**: AWS DynamoDB
- **Authentication**: JWT tokens
- **Payments**: Stripe
- **Email**: AWS SES
- **Deployment**: AWS Lambda + API Gateway

## Project Structure

```
api/
├── handlers/           # Lambda function handlers
│   ├── auth.py        # Authentication endpoints
│   ├── users.py       # User management
│   ├── payments.py    # Stripe integration
│   ├── usage.py       # Usage tracking
│   ├── analytics.py   # Event tracking
│   ├── emails.py      # Email service
│   └── waitlist.py    # Waitlist management
├── models/            # Data models
│   └── user.py        # User model
├── utils/             # Utility functions
│   ├── auth.py        # JWT utilities
│   ├── database.py    # DynamoDB client
│   └── response.py    # API response helpers
├── serverless.yml     # Serverless configuration
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Setup

1. **Install dependencies**:
   ```bash
   npm install
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **AWS Configuration**:
   - Install AWS CLI
   - Configure credentials: `aws configure`
   - Ensure you have appropriate IAM permissions

4. **Stripe Configuration**:
   - Get API keys from Stripe Dashboard
   - Configure webhook endpoint after deployment

## Deployment

### Development
```bash
npm run deploy:dev
```

### Production
```bash
npm run deploy:prod
```

## API Endpoints

### Authentication
- `POST /auth/signup` - User registration
- `POST /auth/login` - User login  
- `POST /auth/refresh` - Refresh access token
- `POST /auth/verify-email` - Verify email address

### User Management
- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update user profile
- `DELETE /users/me` - Delete user account
- `GET /users/usage` - Get usage statistics

### Payments
- `POST /stripe/create-checkout-session` - Create Stripe checkout
- `POST /stripe/webhook` - Stripe webhook handler
- `GET /users/billing` - Get billing information
- `POST /users/billing/cancel` - Cancel subscription

### Analytics
- `POST /analytics/track` - Track custom event
- `GET /analytics` - Get analytics data

### Waitlist
- `POST /waitlist/join` - Join waitlist

### Email
- `POST /emails/welcome` - Send welcome email
- `POST /emails/notification` - Send notification email

## Environment Variables

Required environment variables:

- `JWT_SECRET_KEY` - Secret key for JWT tokens
- `STRIPE_SECRET_KEY` - Stripe secret key
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook secret
- `REDIS_URL` - Redis connection URL (optional)
- `SES_REGION` - AWS SES region

## Database Schema

### Users Table
- `user_id` (Hash Key) - Unique user identifier
- `email` (GSI) - User email address
- `first_name` - User's first name
- `last_name` - User's last name
- `plan` - Subscription plan (free, growth, pro)
- `password_hash` - Hashed password
- `email_verified` - Email verification status
- `created_at` - Account creation timestamp
- `updated_at` - Last update timestamp
- `stripe_customer_id` - Stripe customer ID
- `preferences` - User preferences object

### Usage Table
- `user_id` (Hash Key) - User identifier
- `date_feature` (Range Key) - Date#feature format
- `count` - Usage count

### Analytics Table
- `event_type` (Hash Key) - Type of event
- `timestamp` (Range Key) - Event timestamp
- `user_id` - User identifier (optional)
- `event_data` - Event metadata

### Waitlist Table
- `email` (Hash Key) - Email address
- `source` - Signup source
- `joined_at` - Signup timestamp
- `status` - Waitlist status

## Authentication Flow

1. **User Registration**:
   - POST to `/auth/signup`
   - Creates user record
   - Returns JWT tokens

2. **User Login**:
   - POST to `/auth/login`
   - Validates credentials
   - Returns JWT tokens

3. **API Requests**:
   - Include `Authorization: Bearer <token>` header
   - Token validated by Lambda authorizer

## Payment Flow

1. **Subscription Creation**:
   - POST to `/stripe/create-checkout-session`
   - Redirects to Stripe Checkout
   - Webhook updates user plan

2. **Subscription Management**:
   - Handled via Stripe Customer Portal
   - Webhooks update user status

## Usage Tracking

Usage is tracked per user per month:

- `analyses` - Stock analysis runs
- `backtests` - Strategy backtests
- `portfolio_optimizations` - Portfolio optimizations
- `api_calls` - API requests

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "message": "Error description",
  "error_code": "ERROR_CODE",
  "details": {}
}
```

## Security

- JWT tokens for authentication
- Password hashing with bcrypt
- Input validation with Pydantic
- CORS configuration
- Environment variable protection

## Development

### Local Testing
```bash
npm run offline
```

### Running Tests
```bash
npm run test
```

### Code Formatting
```bash
npm run format
npm run lint
```

## Monitoring

- CloudWatch logs for all Lambda functions
- Error tracking and alerting
- Performance metrics
- Usage analytics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.