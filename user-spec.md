# InvestForge User Specifications

## Overview
InvestForge is an AI-powered investment analysis platform that provides professional-grade financial analysis through a multi-agent AI system. The platform combines automated analysis with an intuitive web interface to help users make informed investment decisions.

## Architecture
- **Frontend**: Streamlit web application
- **Backend**: AWS Lambda functions with API Gateway
- **Database**: DynamoDB for user data, analytics, and usage tracking
- **AI Engine**: CrewAI multi-agent system for financial analysis
- **Infrastructure**: ECS Fargate for app hosting, CloudFront for content delivery

## Current Implementation Status

### ✅ Completed Features

#### Authentication & User Management
- **Login/Signup**: Complete authentication flow with JWT tokens
- **User Registration**: Account creation with plan selection (Free/Growth/Pro)
- **Password Security**: PBKDF2 hashing with salt, complexity validation
- **Rate Limiting**: Token bucket algorithm for API protection
- **Account Lockout**: Automatic lockout after failed login attempts
- **Session Management**: Secure token handling with expiration
- **Demo Mode**: Guest access for feature exploration

#### Security Features
- **Enhanced Authentication**: Multi-layer security with rate limiting
- **Input Validation**: Comprehensive request validation
- **CORS Configuration**: Proper cross-origin resource sharing
- **Error Handling**: Detailed error messages and logging
- **Audit Logging**: Event tracking for security monitoring

#### Core Application
- **Landing Page**: Professional marketing site (investforge.io)
- **Main Application**: Investment analysis interface (investforge.io/app)
- **API Endpoints**: RESTful API for all backend operations (investforge.io/api)
- **Analytics Tracking**: User behavior and feature usage monitoring
- **Usage Limits**: Plan-based feature restrictions and tracking

#### User Interface
- **Responsive Design**: Mobile-friendly layout with modern styling
- **Navigation**: Sidebar navigation with user status and plan info
- **Analysis Interface**: Adaptive interface (beginner/standard/tutorial modes)
- **Progress Tracking**: Visual feedback during analysis operations
- **Error Boundaries**: Graceful error handling and user feedback

#### Infrastructure
- **AWS Deployment**: Full production deployment on AWS
- **Load Balancing**: Application Load Balancer with health checks
- **Auto Scaling**: ECS Fargate with automatic scaling
- **SSL/TLS**: Secure HTTPS with custom domain
- **Monitoring**: CloudWatch logging and monitoring

#### Young Investor Features (NEW)
- **Enhanced Onboarding**: 5-step comprehensive onboarding with demographics collection
- **Scenario-Based Risk Assessment**: Real-world investment scenarios instead of abstract sliders
- **Personalized Stock Suggestions**: Age and goal-based company recommendations
- **Tutorial Analysis Mode**: Guided first analysis with educational explanations
- **Achievement System**: Gamification with progress tracking and unlockable badges
- **Adaptive Interface**: Different UI experiences for beginners vs. experienced users
- **Enhanced Preference Structure**: Comprehensive user profiling and preference management

### 🔄 Partially Implemented Features

#### Young Investor Features - Phase 2 (70% Complete)
**Status**: Core Infrastructure Complete, UI Polish Pending
- **✅ Tutorial Analysis**: Guided first analysis with educational content
- **✅ Achievement Backend**: Full database and API infrastructure for gamification
- **🔄 Contextual Learning**: Tooltip and educational content system (pending)
- **🔄 Visual Achievement Badges**: UI components for achievement display (pending)

#### Password Reset Flow
**Status**: UI Complete, Backend Partial
- **Frontend**: Complete forgot password form and navigation
- **Backend Handlers**: Comprehensive password reset logic in `api/handlers/auth_reset.py`
- **Missing**: Lambda function deployment, email service integration

**Components**:
- `request_password_reset()` - Send reset email with token
- `reset_password()` - Validate token and update password  
- `verify_email_token()` - Email verification functionality
- `check_reset_token_validity()` - Token validation endpoint

#### AI Analysis Engine
**Status**: Framework Ready, Integration Pending
- **Crew System**: Multi-agent AI framework configured
- **Analysis Types**: Technical, fundamental, sentiment, competitor analysis
- **Data Sources**: Yahoo Finance integration for market data
- **Missing**: Full AI crew implementation and model integration

### 📋 Pending Implementation

#### Young Investor Features - Phase 3 & 4
- **Age-Based Recommendation Engine**: Smart stock suggestions based on user demographics
- **Income-Based Investment Suggestions**: Financial guidance tailored to income brackets
- **Goal-Aligned Content Customization**: Personalized content based on investment objectives
- **Conversational Interface Elements**: Interactive chat-like guidance
- **Skip Options for Experienced Users**: Streamlined flow for advanced investors
- **Personalized Investment Roadmap**: Custom learning and investment paths
- **Analytics Dashboard**: Onboarding and engagement metrics visualization

#### Email Services
- **AWS SES Configuration**: Email sending service setup
- **Email Templates**: Password reset and verification email templates
- **Email Verification**: Account activation via email
- **Notification System**: User communication infrastructure

#### Advanced Features
- **Portfolio Management**: User portfolio tracking and analysis
- **Backtesting**: Historical strategy testing
- **Risk Assessment**: Portfolio risk analysis
- **Educational Content**: Investment learning resources
- **Payment Integration**: Stripe integration for plan upgrades

#### Admin & Analytics
- **Admin Dashboard**: User management and system monitoring
- **Advanced Analytics**: Detailed usage and performance metrics
- **GDPR Compliance**: Data privacy and user rights management
- **Audit Logging**: Comprehensive security and usage logging

## Technical Specifications

### Authentication Flow
1. User enters credentials on login form
2. Frontend validates input and calls `/api/auth/login`
3. Lambda function validates against DynamoDB
4. JWT token returned on successful authentication
5. Token stored in session state for API calls
6. Automatic token refresh before expiration

### Password Reset Flow (To Be Completed)
1. User clicks "Forgot Password?" on login form
2. User enters email on reset form
3. Frontend calls `/api/auth/forgot-password` (needs Lambda)
4. Backend generates reset token and sends email (needs SES)
5. User clicks link in email to reset form
6. User enters new password with token validation
7. Backend updates password and invalidates token

### Data Models

#### User
```json
{
  "user_id": "uuid",
  "email": "string",
  "password_hash": "string", 
  "first_name": "string",
  "last_name": "string",
  "plan": "free|growth|pro",
  "status": "active|suspended",
  "email_verified": "boolean",
  "created_at": "iso_datetime",
  "updated_at": "iso_datetime",
  "last_login": "iso_datetime",
  "preferences": "enhanced_preferences_object"
}
```

#### Enhanced User Preferences (NEW)
```json
{
  "demographics": {
    "age_range": "16-20 (High school/Early college)",
    "income_range": "$25k-50k"
  },
  "investment_goals": {
    "primary_goal": "Learn investing basics",
    "timeline": "5-10 years"
  },
  "risk_assessment": {
    "risk_score": 8,
    "risk_profile": "Growth-Oriented",
    "scenario_responses": {
      "scenario1": "Hold knowing markets recover long-term",
      "scenario2": "Broad market fund",
      "scenario3": "Focus on growth with mostly stocks"
    }
  },
  "financial_status": {
    "initial_amount": "$500-1,000",
    "has_emergency_fund": true
  },
  "tutorial_preferences": {
    "tutorial_stock": "AAPL",
    "suggested_stocks": {"AAPL": "Tech giant you use daily"},
    "tutorial_completed": true
  },
  "achievements": {
    "unlocked": ["first_analysis", "risk_assessment"],
    "progress": {
      "first_analysis": {"unlocked_at": "2024-01-01T00:00:00Z"}
    }
  },
  "analysis_preferences": {
    "default_depth": "standard",
    "show_tooltips": true,
    "show_educational_content": true
  },
  "onboarding_completed_at": "iso_datetime",
  "last_updated": "iso_datetime"
}
```

#### Analytics Event
```json
{
  "event_id": "uuid",
  "event_type": "string",
  "user_id": "string",
  "timestamp": "iso_datetime",
  "event_data": "object",
  "source": "api|lambda|app"
}
```

#### Young Investor Analytics Events (NEW)
- `onboarding_completed` - Demographics, risk profile, goals
- `tutorial_analysis_started` - Tutorial engagement tracking
- `achievement_unlocked` - Gamification progress
- `risk_assessment_completed` - Scenario-based risk tolerance
- `personalized_suggestion` - Stock recommendation interactions
- `beginner_interface_interaction` - UI adaptation usage

### API Endpoints

#### Authentication
- `POST /api/auth/signup` - User registration
- `POST /api/auth/login` - User authentication
- `POST /api/auth/refresh` - Token refresh (if implemented)
- `POST /api/auth/forgot-password` - Request password reset (pending)
- `POST /api/auth/reset-password` - Reset password with token (pending)

#### Enhanced Preferences (NEW)
- `GET /api/preferences/enhanced` - Get enhanced user preferences
- `PUT /api/preferences/enhanced` - Update enhanced user preferences
- `POST /api/preferences/legacy` - Legacy compatibility endpoint

#### Achievements (NEW)
- `GET /api/achievements` - Get user achievements and progress
- `POST /api/achievements/unlock` - Unlock an achievement
- `PUT /api/achievements/progress` - Update achievement progress

#### Analytics
- `POST /api/analytics/track` - Track user events
- `GET /api/analytics/dashboard` - Get analytics data (admin)
- `GET /api/analytics/onboarding` - Get onboarding analytics (admin)
- `GET /api/analytics/onboarding/me` - Get user onboarding metrics

#### Users
- `GET /api/users/me` - Get current user profile
- `PUT /api/users/me` - Update user profile
- `GET /api/users/preferences` - Get user preferences (legacy)
- `PUT /api/users/preferences` - Update user preferences (legacy)

### Environment Configuration

#### Lambda Environment Variables
```
DYNAMODB_TABLE_USERS=investforge-users-simple
DYNAMODB_TABLE_ANALYTICS=investforge-analytics
DYNAMODB_TABLE_USAGE=investforge-usage
JWT_SECRET_KEY=dev-secret-key-change-in-production
```

#### Streamlit App Environment
```
API_BASE_URL=https://investforge.io/api
APP_URL=https://investforge.io/app
```

## Development Roadmap

### Phase 1: Young Investor Foundation ✅ COMPLETED
1. ✅ Enhanced onboarding with demographics collection
2. ✅ Scenario-based risk assessment
3. ✅ Investment amount with contextual guidance
4. ✅ Tutorial analysis mode
5. ✅ Database schema and API infrastructure

### Phase 2: Enhanced Learning Experience (70% Complete)
1. ✅ Beginner stock analysis tutorial
2. 🔄 Contextual learning system with tooltips
3. 🔄 Achievement system with visual badges
4. ⏳ Interactive educational content

### Phase 3: Personalization Engine (Pending)
1. ⏳ Age-based recommendation engine
2. ⏳ Income-based investment suggestions
3. ⏳ Goal-aligned content customization
4. ⏳ Analytics dashboard for onboarding metrics

### Phase 4: Advanced Interaction (Pending)
1. ⏳ Conversational interface elements
2. ⏳ Skip options for experienced users
3. ⏳ Personalized investment roadmap
4. ⏳ Advanced achievement system

### Phase 5: Infrastructure & Integration
1. ⏳ **Complete Password Reset Flow**
   - Create Lambda functions for password reset endpoints (`lambda_forgot_password.py`, `lambda_reset_password.py`)
   - Configure AWS SES for email delivery with custom templates
   - Add API client methods in Streamlit app (`forgot_password()`, `reset_password()` methods)
   - Connect frontend forms to backend APIs (forgot password UI integration)
   - Test complete password reset flow (end-to-end validation)
   - Deploy Lambda functions to production environment
   - Set up SES domain verification and email templates
2. ⏳ AI analysis enhancement (CrewAI integration)
3. ⏳ Portfolio management system
4. ⏳ Payment integration and plan upgrades

### Phase 6: Enterprise Features
1. ⏳ Admin dashboard with young investor metrics
2. ⏳ Advanced analytics and reporting
3. ⏳ GDPR compliance and data management
4. ⏳ Multi-user workspaces

## Security Considerations

### Current Security Measures
- Password hashing with PBKDF2 and salt
- Rate limiting on authentication endpoints
- Account lockout after failed attempts
- JWT token expiration and refresh
- Input validation and sanitization
- CORS configuration
- HTTPS enforcement

### Additional Security Needs
- Email verification enforcement
- Two-factor authentication (2FA)
- Session timeout policies
- IP-based restrictions
- Advanced threat detection
- Security headers and CSP

## Performance Requirements

### Current Performance
- Sub-second API response times
- Auto-scaling ECS infrastructure
- CloudFront CDN for static assets
- Optimized database queries

### Performance Goals
- <100ms API response times
- Support for 10,000+ concurrent users
- 99.9% uptime SLA
- Global content delivery

## Compliance & Privacy

### Current Compliance
- Basic data protection practices
- Secure data transmission
- User consent for analytics

### Required Compliance
- GDPR compliance implementation
- SOC 2 Type II certification
- PCI DSS for payment processing
- Data retention policies
- User data export/deletion

## Young Investor Feature Summary

### ✅ Completed Components
- **Enhanced Onboarding System**: 5-step comprehensive flow with demographics, risk scenarios, and financial guidance
- **Database Architecture**: Complete preference structure with validation and migration support
- **API Infrastructure**: Full CRUD operations for preferences, achievements, and analytics
- **Tutorial Analysis Mode**: Educational first-time analysis experience with guided explanations
- **Achievement Backend**: Complete gamification infrastructure with progress tracking
- **Adaptive Interface**: Different UI experiences based on user profile and experience level
- **Analytics Framework**: Comprehensive tracking for onboarding metrics and user behavior

### 🔄 In Progress (Phase 2)
- **Contextual Learning System**: Tooltip and educational content integration
- **Visual Achievement Badges**: UI components for gamification display

### ⏳ Planned Features (Phase 3-4)
- **Smart Recommendation Engine**: Age and income-based stock suggestions
- **Goal-Aligned Personalization**: Content customization based on investment objectives
- **Conversational Interface**: Interactive guidance and chat-like elements
- **Investment Roadmap**: Personalized learning and investment paths

### 📊 Success Metrics Tracking
- **Onboarding Completion Rate**: >80% (tracked via analytics)
- **Time to Complete**: <10 minutes (measured via event timestamps)
- **First Analysis Within 7 Days**: 90% (tracked via tutorial completion)
- **User Satisfaction**: >4.5/5 (to be implemented via feedback system)

---

*Last Updated: September 30, 2025*
*Version: 2.0 - Young Investor Features*