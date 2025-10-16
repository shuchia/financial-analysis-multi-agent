# Portfolio Snapshots Feature Design

**Status:** Design Complete - Ready for Implementation
**Created:** 2025-10-16
**Priority:** Future Enhancement (After Bug Fixes)

---

## 🎯 Feature Overview

**Current Scope (Phase 1):** Save portfolio with user preferences at a point in time
**Future Scope (Phase 2+):** Multiple portfolios, comparison tools, parameter variations

### User Story
> "As an InvestForge user, I want to save my portfolio at a specific point in time with all my preferences (risk tolerance, timeline, investment amount), so I can refer back to it later and eventually create multiple portfolios to compare different strategies."

---

## 📊 Data Model

### Portfolio Snapshot Structure

```python
{
    "portfolio_id": "port_123abc...",           # Unique identifier
    "user_id": "user_email@example.com",        # From session/auth
    "created_at": "2025-10-16T14:30:00Z",      # Timestamp
    "name": "Conservative Retirement 2025",     # User-provided or auto-generated

    # User Preferences (at time of save)
    "preferences": {
        "risk_profile": "conservative",         # conservative|moderate|aggressive
        "risk_score": 0.3,                      # 0.0 - 1.0
        "timeline": "Long-term (10+ years)",
        "investment_amount": 10000.00,
        "investment_goals": ["retirement", "wealth_building"]
    },

    # Portfolio Composition
    "allocations": [
        {
            "ticker": "VOO",
            "percentage": 40.0,
            "amount": 4000.00,
            "reasoning": "Core broad market exposure",
            "category": "Large Cap ETF"
        },
        {
            "ticker": "BND",
            "percentage": 30.0,
            "amount": 3000.00,
            "reasoning": "Stability and income",
            "category": "Bond ETF"
        }
        # ... more allocations
    ],

    # Risk Metrics (if available)
    "risk_metrics": {
        "sharpe_ratio": 1.23,
        "annual_volatility": 12.5,
        "value_at_risk_95": 8.2,
        "max_drawdown": 15.3,
        # ... from VaR calculator tool
    },

    # Optimization Results (if user ran optimization)
    "optimization_results": {
        "max_sharpe_portfolio": {
            "weights": {...},
            "expected_return": 0.085,
            "volatility": 0.125,
            "sharpe_ratio": 1.45
        },
        "was_applied": false  # Did user apply optimized allocation?
    },

    # Metadata
    "status": "active",                         # active|archived
    "tags": ["2025-Q4", "initial"],            # User-defined tags
    "notes": "First portfolio based on...",     # User notes

    # Future fields (optional for now)
    "parent_portfolio_id": null,               # For portfolio variations
    "comparison_group": null                   # For grouping related portfolios
}
```

---

## 🏗️ Technical Architecture

### Storage Layer

**Recommendation: DynamoDB** (already using AWS ecosystem)

```
Table: InvestForge-Portfolios
Primary Key: portfolio_id (String)
Sort Key: user_id (String)
GSI-1: user_id (PK), created_at (SK)  # Query all user portfolios by date
GSI-2: user_id (PK), status (SK)      # Query active vs archived
```

**Alternative:** PostgreSQL/RDS if you want relational queries and complex joins for future comparison features

**Cost Estimate:**
- DynamoDB: ~$0.25/GB/month storage + $0.25 per million reads
- Expected: <$5/month for first 1000 users

---

## 🔌 API Design

### Phase 1: Single Portfolio Save

#### **POST /api/portfolio/save**
```json
Request:
{
    "user_id": "user@example.com",
    "name": "My Conservative Portfolio",  // Optional, auto-generate if null
    "preferences": { ... },
    "allocations": [ ... ],
    "risk_metrics": { ... },  // Optional
    "optimization_results": { ... },  // Optional
    "tags": ["initial", "2025"],  // Optional
    "notes": ""  // Optional
}

Response:
{
    "success": true,
    "portfolio_id": "port_abc123",
    "message": "Portfolio saved successfully"
}
```

#### **GET /api/portfolio/{portfolio_id}**
```json
Response:
{
    "success": true,
    "portfolio": { ... full portfolio object ... }
}
```

#### **GET /api/portfolio/user/{user_id}/latest**
```json
Response:
{
    "success": true,
    "portfolio": { ... most recent portfolio ... }
}
```

### Future Phase 2: Multiple Portfolios

#### **GET /api/portfolio/user/{user_id}/list**
Query Parameters:
- `status`: active|archived
- `tags`: comma-separated
- `from_date`, `to_date`: date range
- `limit`, `offset`: pagination

#### **POST /api/portfolio/{portfolio_id}/compare**
Compare two or more portfolios

#### **PUT /api/portfolio/{portfolio_id}/update**
Update name, tags, notes, status (not core allocations)

#### **POST /api/portfolio/{portfolio_id}/clone**
Create new portfolio based on existing one with parameter changes

---

## 🎨 UI/UX Flow (Phase 1)

### 1. Save Portfolio Button Location

**Placement:** At the top of Portfolio Results page, next to "Generate New Portfolio"

```
┌─────────────────────────────────────────────────┐
│ 🎉 Your Personalized Portfolio                  │
│                                                  │
│ [💾 Save Portfolio]  [🔄 Generate New Portfolio]│
└─────────────────────────────────────────────────┘
```

### 2. Save Portfolio Dialog

```
┌────────────────────────────────────────────┐
│  💾 Save Portfolio Snapshot                │
├────────────────────────────────────────────┤
│                                            │
│  Portfolio Name:                           │
│  [Auto-generated or enter custom name     ]│
│                                            │
│  Tags (optional):                          │
│  [retirement] [initial] [+ Add tag]       │
│                                            │
│  Notes (optional):                         │
│  [First portfolio based on moderate risk, │
│   10-year timeline...]                     │
│                                            │
│  ✅ This snapshot includes:                │
│     • Your preferences (risk, timeline)    │
│     • Portfolio allocation (5 holdings)    │
│     • Risk analysis results                │
│     • Optimization results (if run)        │
│                                            │
│  [Cancel]              [💾 Save Portfolio] │
└────────────────────────────────────────────┘
```

### 3. Success Confirmation

```
✅ Portfolio saved successfully!
   "Conservative Retirement 2025"

   You can access this portfolio anytime from
   your dashboard.

   [View Dashboard]  [Continue Editing]
```

### 4. Auto-Name Generation Logic

If user doesn't provide a name, generate from:
```python
"{risk_profile.title()} {primary_goal} {year}"

Examples:
- "Conservative Retirement 2025"
- "Aggressive Growth 2025"
- "Moderate Wealth Building 2025"
```

---

## 💻 Implementation Specifications

### Phase 1: Minimum Viable Feature

#### Backend Implementation

**New Lambda Function:** `investforge-save-portfolio`

**Location:** `api/save-portfolio/handler.py`

```python
import boto3
import json
from datetime import datetime
import uuid

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('InvestForge-Portfolios')

def lambda_handler(event, context):
    """Save portfolio snapshot to DynamoDB"""

    body = json.loads(event['body'])

    # Validate required fields
    if not body.get('user_id'):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'user_id is required'})
        }

    if not body.get('allocations'):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'allocations are required'})
        }

    # Generate portfolio_id
    portfolio_id = f"port_{uuid.uuid4().hex[:12]}"

    # Auto-generate name if not provided
    if not body.get('name'):
        preferences = body.get('preferences', {})
        risk = preferences.get('risk_profile', 'balanced').title()
        goals = preferences.get('investment_goals', ['investing'])
        primary_goal = goals[0].replace('_', ' ').title() if goals else 'Portfolio'
        year = datetime.now().year
        body['name'] = f"{risk} {primary_goal} {year}"

    # Create portfolio object
    portfolio = {
        'portfolio_id': portfolio_id,
        'user_id': body['user_id'],
        'created_at': datetime.utcnow().isoformat(),
        'name': body['name'],
        'preferences': body.get('preferences', {}),
        'allocations': body.get('allocations', []),
        'risk_metrics': body.get('risk_metrics'),
        'optimization_results': body.get('optimization_results'),
        'status': 'active',
        'tags': body.get('tags', []),
        'notes': body.get('notes', '')
    }

    # Save to DynamoDB
    try:
        table.put_item(Item=portfolio)

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'success': True,
                'portfolio_id': portfolio_id,
                'message': 'Portfolio saved successfully'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
```

**Serverless Configuration:** `api/serverless.yml`

```yaml
functions:
  # ... existing functions ...

  savePortfolio:
    handler: save-portfolio/handler.lambda_handler
    name: investforge-save-portfolio
    events:
      - http:
          path: portfolio/save
          method: post
          cors: true
    environment:
      PORTFOLIOS_TABLE: InvestForge-Portfolios

resources:
  Resources:
    PortfoliosTable:
      Type: AWS::DynamoDB::Table
      Properties:
        TableName: InvestForge-Portfolios
        BillingMode: PAY_PER_REQUEST
        AttributeDefinitions:
          - AttributeName: portfolio_id
            AttributeType: S
          - AttributeName: user_id
            AttributeType: S
          - AttributeName: created_at
            AttributeType: S
          - AttributeName: status
            AttributeType: S
        KeySchema:
          - AttributeName: portfolio_id
            KeyType: HASH
          - AttributeName: user_id
            KeyType: RANGE
        GlobalSecondaryIndexes:
          - IndexName: UserPortfoliosByDate
            KeySchema:
              - AttributeName: user_id
                KeyType: HASH
              - AttributeName: created_at
                KeyType: RANGE
            Projection:
              ProjectionType: ALL
          - IndexName: UserPortfoliosByStatus
            KeySchema:
              - AttributeName: user_id
                KeyType: HASH
              - AttributeName: status
                KeyType: RANGE
            Projection:
              ProjectionType: ALL
```

#### Frontend Implementation

**New Component:** `app/components/save_portfolio_dialog.py`

```python
import streamlit as st
import requests
from datetime import datetime

def show_save_portfolio_dialog(
    structured_portfolio,
    user_profile,
    investment_amount,
    timeline,
    risk_metrics=None,
    optimization_results=None
):
    """Display save portfolio dialog"""

    # Auto-generate default name
    risk = user_profile.get('risk_profile', 'moderate').title()
    goals = user_profile.get('investment_goals', ['investing'])
    primary_goal = goals[0].replace('_', ' ').title() if goals else 'Portfolio'
    year = datetime.now().year
    default_name = f"{risk} {primary_goal} {year}"

    # Dialog content
    st.markdown("### 💾 Save Portfolio Snapshot")
    st.markdown("---")

    # Portfolio name input
    portfolio_name = st.text_input(
        "Portfolio Name",
        value=default_name,
        help="Give your portfolio a memorable name"
    )

    # Tags input
    st.write("**Tags** (optional)")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        tag1 = st.text_input("Tag 1", value=str(year), label_visibility="collapsed")
    with col2:
        tag2 = st.text_input("Tag 2", value="initial", label_visibility="collapsed")

    tags = [t for t in [tag1, tag2] if t]

    # Notes
    notes = st.text_area(
        "**Notes** (optional)",
        placeholder="Add any notes about this portfolio...",
        height=100
    )

    # Summary of what's being saved
    st.markdown("---")
    st.markdown("#### ✅ This snapshot includes:")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"• Risk Profile: **{user_profile.get('risk_profile', 'N/A').title()}**")
        st.write(f"• Timeline: **{timeline}**")
        st.write(f"• Investment: **${investment_amount:,.0f}**")
    with col2:
        st.write(f"• Holdings: **{len(structured_portfolio['tickers'])} positions**")
        if risk_metrics:
            st.write("• ✅ Risk Analysis included")
        if optimization_results:
            st.write("• ✅ Optimization Results included")

    st.markdown("---")

    # Action buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Cancel", use_container_width=True):
            st.session_state.show_save_dialog = False
            st.rerun()

    with col2:
        if st.button("💾 Save Portfolio", type="primary", use_container_width=True):
            # Prepare payload
            payload = {
                'user_id': st.session_state.get('user_email', 'guest@investforge.io'),
                'name': portfolio_name,
                'preferences': {
                    'risk_profile': user_profile.get('risk_profile'),
                    'risk_score': user_profile.get('risk_score'),
                    'timeline': timeline,
                    'investment_amount': investment_amount,
                    'investment_goals': user_profile.get('investment_goals', [])
                },
                'allocations': structured_portfolio.get('allocations', []),
                'risk_metrics': risk_metrics,
                'optimization_results': optimization_results,
                'tags': tags,
                'notes': notes
            }

            # Call API
            try:
                response = requests.post(
                    'https://investforge.io/api/portfolio/save',
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    st.session_state.saved_portfolio_id = result['portfolio_id']
                    st.session_state.show_save_dialog = False
                    st.success(f"✅ Portfolio saved: **{portfolio_name}**")
                    st.balloons()

                    # Future: Show link to dashboard
                    # st.markdown(f"[View in Dashboard](/dashboard?portfolio={result['portfolio_id']})")
                else:
                    st.error(f"Failed to save portfolio: {response.text}")
            except Exception as e:
                st.error(f"Error saving portfolio: {str(e)}")
```

**Integration in `app/app.py`:**

```python
# Import the component
from components.save_portfolio_dialog import show_save_portfolio_dialog

# In show_portfolio_results() function, add button in header area
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("💾 Save Portfolio", type="secondary", use_container_width=True):
        st.session_state.show_save_dialog = True

with col2:
    if st.button("🔄 Generate New Portfolio", use_container_width=True):
        # Existing functionality
        pass

# Show dialog if triggered
if st.session_state.get('show_save_dialog', False):
    show_save_portfolio_dialog(
        structured_portfolio=structured_portfolio,
        user_profile=user_profile,
        investment_amount=investment_amount,
        timeline=timeline,
        risk_metrics=st.session_state.get('portfolio_risk_analysis'),
        optimization_results=st.session_state.get('portfolio_optimization_crew')
    )
```

---

## 🚀 Future Extensions (Phase 2+)

### Portfolio Management Dashboard

**New Page:** `/dashboard` or `/my-portfolios`

**Features:**
- List all saved portfolios
- Filter by status (active/archived)
- Search by name or tags
- Sort by date, amount, risk
- Quick actions: View, Clone, Compare, Archive

**UI Wireframe:**

```
┌─────────────────────────────────────────────────┐
│ 📊 My Portfolios                                │
├─────────────────────────────────────────────────┤
│                                                  │
│ [🆕 Create New] [🗂️ Active (3)] [📦 Archived (1)]│
│                                                  │
│ Search: [____________] Sort: [Recent ▼]         │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Conservative Retirement 2025      Oct 16   │  │
│ │ $10,000 • 5 holdings • Moderate Risk       │  │
│ │ Sharpe: 1.23 | Volatility: 12.5%           │  │
│ │ Tags: 2025, initial                        │  │
│ │ [View] [Clone] [Compare] [Archive]         │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Aggressive Growth 2025            Oct 10   │  │
│ │ $15,000 • 8 holdings • High Risk           │  │
│ │ Sharpe: 1.45 | Volatility: 18.2%           │  │
│ │ Tags: 2025, growth                         │  │
│ │ [View] [Clone] [Compare] [Archive]         │  │
│ └────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Portfolio Comparison View

**Features:**
- Select 2-4 portfolios to compare
- Side-by-side metrics display
- Highlight differences
- Allocation overlap analysis
- Performance projections comparison

**UI Wireframe:**

```
┌─────────────────────────────────────────────────┐
│ 📊 Compare Portfolios                           │
├─────────────────────────────────────────────────┤
│                                                  │
│  Portfolio A        vs    Portfolio B           │
│  Conservative             Aggressive            │
│  ────────────────────────────────────────────   │
│  Risk: Moderate    |      Risk: High            │
│  Amount: $10K      |      Amount: $15K          │
│  Holdings: 5       |      Holdings: 8           │
│  Sharpe: 1.23      |      Sharpe: 1.45          │
│  Volatility: 12%   |      Volatility: 18%       │
│  VaR 95%: 8.2%     |      VaR 95%: 12.5%        │
│                                                  │
│  Common Holdings: VOO, BND                      │
│  Unique to A: SCHD, VNQ                         │
│  Unique to B: QQQ, ARKK, VWO                    │
│                                                  │
│  [Download Report] [Save Comparison] [Close]    │
└─────────────────────────────────────────────────┘
```

### Parameter Variation (Clone & Modify)

**Features:**
- Start from existing portfolio
- Modify one or more parameters:
  - Risk profile
  - Investment amount
  - Timeline
  - Specific holdings
- Generate new portfolio with modifications
- Link to parent portfolio

**UI Wireframe:**

```
┌────────────────────────────────────────────┐
│  Create Portfolio Variation                │
├────────────────────────────────────────────┤
│  Base Portfolio: "Conservative Retirement" │
│                                            │
│  What would you like to change?            │
│                                            │
│  ☑ Risk Profile:                           │
│     [Moderate ▼] (was Conservative)        │
│                                            │
│  ☑ Investment Amount:                      │
│     [$20,000] (was $10,000)               │
│                                            │
│  ☐ Timeline:                               │
│     [Long-term (10+ years) ▼] (unchanged) │
│                                            │
│  ☐ Specific Holdings:                      │
│     [Modify individual allocations]        │
│                                            │
│  New Portfolio Name:                       │
│  [Moderate Retirement 2025 - $20K         ]│
│                                            │
│  [Cancel]    [Generate New Portfolio]      │
└────────────────────────────────────────────┘
```

---

## 📋 Implementation Checklist

### Phase 1: Basic Save Feature

#### Backend
- [ ] Create DynamoDB table `InvestForge-Portfolios` with GSIs
- [ ] Create Lambda function `investforge-save-portfolio`
- [ ] Add API Gateway endpoint `/api/portfolio/save`
- [ ] Implement auto-name generation logic
- [ ] Add validation for required fields
- [ ] Add error handling and logging
- [ ] Test DynamoDB write operations
- [ ] Test API endpoint with various payloads

#### Frontend
- [ ] Create `app/components/` directory if not exists
- [ ] Create `save_portfolio_dialog.py` component
- [ ] Add "Save Portfolio" button to results page header
- [ ] Implement session state for dialog visibility
- [ ] Add tags input functionality
- [ ] Add notes textarea
- [ ] Display portfolio summary in dialog
- [ ] Integrate with save API endpoint
- [ ] Add loading states during save
- [ ] Add success/error notifications
- [ ] Test with various portfolio configurations

#### Testing
- [ ] Unit test auto-name generation
- [ ] Test save with minimal data (allocations only)
- [ ] Test save with full data (risk metrics + optimization)
- [ ] Test with/without custom name
- [ ] Test with/without tags
- [ ] Test with/without notes
- [ ] Test error handling (network failures)
- [ ] Test error handling (validation failures)
- [ ] Performance test (save time < 2 seconds)
- [ ] Load test (100 concurrent saves)

### Phase 2: View Saved Portfolios

#### Backend
- [ ] Create Lambda function `investforge-get-portfolios`
- [ ] Implement GET `/api/portfolio/{portfolio_id}`
- [ ] Implement GET `/api/portfolio/user/{user_id}/list`
- [ ] Add pagination support
- [ ] Add filtering by status, tags, date range
- [ ] Add sorting options

#### Frontend
- [ ] Create portfolio dashboard page
- [ ] List all user portfolios
- [ ] Add search functionality
- [ ] Add filter by status
- [ ] Add filter by tags
- [ ] Add sort options
- [ ] Implement portfolio card component
- [ ] Add "View Details" functionality
- [ ] Add pagination controls

### Phase 3: Portfolio Management

#### Backend
- [ ] Implement PUT `/api/portfolio/{portfolio_id}/update`
- [ ] Implement DELETE `/api/portfolio/{portfolio_id}` (soft delete)
- [ ] Add archive/unarchive functionality

#### Frontend
- [ ] Add archive/unarchive button
- [ ] Add edit metadata dialog
- [ ] Add delete confirmation dialog
- [ ] Update portfolio list on changes

### Phase 4: Comparison & Variations

#### Backend
- [ ] Create Lambda function `investforge-compare-portfolios`
- [ ] Implement POST `/api/portfolio/{id}/compare`
- [ ] Calculate comparison metrics
- [ ] Implement POST `/api/portfolio/{id}/clone`
- [ ] Add parent-child portfolio linking

#### Frontend
- [ ] Create comparison page
- [ ] Multi-select portfolios
- [ ] Side-by-side comparison view
- [ ] Difference highlighting
- [ ] Create variation dialog
- [ ] Parameter modification UI
- [ ] Link related portfolios visualization

---

## 🎯 Success Metrics

### Phase 1 KPIs
- **Adoption Rate:** % of users who save at least one portfolio within first session
  - Target: >40%
- **Save Completion:** % of users who complete save dialog
  - Target: >80%
- **Average Time to Save:** Time from clicking button to successful save
  - Target: <30 seconds

### Phase 2+ KPIs
- **Engagement:** Average # of portfolios saved per user
  - Target: 2-3 portfolios
- **Return Rate:** Users returning to view saved portfolios
  - Target: >60% within 7 days
- **Comparison Usage:** % of users comparing portfolios
  - Target: >25%
- **Variation Creation:** % of users creating portfolio variations
  - Target: >15%

---

## 💰 Cost Estimate

### AWS Resources (Phase 1)

**DynamoDB:**
- Storage: $0.25/GB/month
- Read/Write: Pay-per-request
- Expected: ~1000 portfolios/month @ 10KB each = 10MB
- Cost: <$1/month

**Lambda:**
- Invocations: $0.20 per 1M requests
- Expected: ~1000 saves/month
- Cost: <$0.01/month

**API Gateway:**
- $3.50 per 1M requests
- Expected: ~1000 requests/month
- Cost: <$0.01/month

**Total Phase 1 Cost:** ~$1-2/month

### Phase 2+ Additional Costs
- More DynamoDB reads for list/view operations: +$1-3/month
- Comparison operations (CPU intensive): +$2-5/month

**Total Projected Cost:** $5-10/month for 1000 active users

---

## 🔒 Security Considerations

1. **Authentication:** Ensure user_id is validated from JWT token
2. **Authorization:** Users can only save/view their own portfolios
3. **Input Validation:** Sanitize all user inputs (name, tags, notes)
4. **Rate Limiting:** Max 10 saves per user per hour
5. **Data Privacy:** Encrypt sensitive portfolio data at rest
6. **GDPR Compliance:** Allow users to export/delete all their data

---

## 📝 Open Questions

1. **Should we limit the number of portfolios a user can save?**
   - Recommendation: Start unlimited, add limits later if needed

2. **Should we auto-save portfolios or require explicit action?**
   - Recommendation: Explicit save only (prevents clutter)

3. **How long should we keep archived portfolios?**
   - Recommendation: Keep indefinitely, allow user to permanently delete

4. **Should we version portfolios or treat each as a separate snapshot?**
   - Recommendation: Separate snapshots for Phase 1, versioning in Phase 3

---

## 🎓 Learning Resources

- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [Streamlit Session State](https://docs.streamlit.io/library/api-reference/session-state)
- [Portfolio Management UX Patterns](https://www.nngroup.com/articles/financial-portfolio-design/)

---

## 📅 Estimated Timeline

**Phase 1 (Basic Save):**
- Backend: 2-3 days
- Frontend: 2-3 days
- Testing: 1 day
- **Total: 5-7 days**

**Phase 2 (View Portfolios):**
- Backend: 2 days
- Frontend: 3-4 days
- **Total: 5-6 days**

**Phase 3 (Management):**
- Backend: 1-2 days
- Frontend: 2-3 days
- **Total: 3-5 days**

**Phase 4 (Comparison):**
- Backend: 3-4 days
- Frontend: 4-5 days
- **Total: 7-9 days**

**Full Implementation:** 20-27 days (4-5 weeks)

---

## 🚦 Status

- [x] Design Complete
- [ ] Ready for Bug Fixes First
- [ ] Phase 1 Implementation Pending
- [ ] Phase 2+ Future Enhancement

**Next Steps:** Address current bugs, then return to implement Phase 1

---

*This document will be updated as implementation progresses and new requirements emerge.*
