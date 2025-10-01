# Onboarding Tests Documentation

This directory contains comprehensive unit tests and integration tests for the young investor onboarding flow.

## Test Structure

### Unit Tests (`test_onboarding.py`)
Tests individual onboarding components in isolation:
- **TestOnboardingComponents**: Tests each step of the onboarding flow
  - Demographics collection
  - Risk assessment scenarios
  - Investment amount recommendations
  - Tutorial functionality
  - Achievement system initialization
  - Action plan generation

- **TestOnboardingFlow**: Tests navigation and flow control
  - Step navigation (forward/backward)
  - Data persistence between steps
  - Skip functionality
  - Completion flow

- **TestOnboardingHelpers**: Tests helper functions
  - Risk score calculation
  - Contextual comparisons
  - Data validation
  - Profile generation

### Integration Tests (`test_integration_onboarding.py`)
Tests complete onboarding journeys end-to-end:
- **TestCompleteOnboardingJourney**: Full user journey scenarios
  - Young college investor journey
  - Working professional investor journey
  - Skip onboarding flow
  - Data flow from start to finish

- **TestOnboardingErrorHandling**: Error scenarios
  - API failures
  - Invalid data handling
  - Network timeout resilience
  - Graceful degradation

- **TestOnboardingAnalytics**: Analytics tracking
  - Event tracking at each step
  - Dropout tracking
  - Completion metrics
  - User behavior analytics

## Running the Tests

### Run All Tests
```bash
python tests/run_tests.py
```

### Run Specific Test Suites
```bash
# Run only unit tests
python tests/run_tests.py --suite unit

# Run only integration tests
python tests/run_tests.py --suite integration
```

### Run Specific Test
```bash
# Run a specific test class
python tests/run_tests.py --test test_onboarding.TestOnboardingComponents

# Run a specific test method
python tests/run_tests.py --test test_onboarding.TestOnboardingComponents.test_demographics_data_collection
```

### Run with Coverage
```bash
# Install coverage.py first
pip install coverage

# Run tests with coverage
python tests/run_tests.py --coverage

# View HTML coverage report
open htmlcov/index.html
```

## Test Coverage Areas

### 1. Demographics Step
- Age range selection
- Income range selection
- Primary goal selection
- Motivation level tracking
- Data persistence

### 2. Risk Assessment
- Scenario-based questions
- Risk score calculation
- Risk profile determination
- Conservative vs aggressive detection

### 3. Investment Amount
- Income-based recommendations
- Contextual comparisons
- Amount validation
- Monthly commitment options

### 4. Tutorial
- Stock suggestions based on profile
- Tutorial completion tracking
- Achievement unlocking
- Learning point coverage

### 5. Action Plan
- Personalized plan generation
- Timeline milestones
- Learning resource recommendations
- Achievement targets

### 6. Error Handling
- API failure recovery
- Invalid data rejection
- Network resilience
- User-friendly error messages

### 7. Analytics
- Step completion tracking
- Time spent analysis
- Dropout detection
- Conversion funnel

## Key Test Patterns

### Mocking Streamlit
```python
# Mock Streamlit session state
st.session_state = {
    'authenticated': True,
    'onboarding_step': 1,
    'onboarding_data': {}
}

# Mock UI components
st.selectbox = Mock(return_value="21-25")
st.button = Mock(return_value=True)
```

### Mocking API Client
```python
mock_api_client = Mock()
mock_api_client.save_user_preferences = Mock(return_value=True)
mock_api_client.track_onboarding_event = Mock(return_value=True)
```

### Testing User Journeys
```python
# Complete all steps sequentially
self._complete_demographics_step(mock_state, journey_data)
self._complete_risk_assessment_step(mock_state, journey_data)
# ... continue through all steps

# Verify final state
self.assertTrue(mock_state['onboarding_complete'])
```

## Expected Test Results

All tests should pass with the following expectations:
- Unit tests: 15+ test methods covering individual components
- Integration tests: 10+ test methods covering full journeys
- Error handling: Graceful failures with user-friendly messages
- Analytics: Complete event tracking at each step

## Maintenance

When modifying the onboarding flow:
1. Update relevant unit tests for component changes
2. Update integration tests for flow changes
3. Add new tests for new features
4. Run full test suite before committing
5. Maintain test coverage above 80%

## Troubleshooting

### Import Errors
Ensure the app directory is in the Python path:
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
```

### Mock Issues
Clear mocks between tests:
```python
def setUp(self):
    # Reset all mocks
    st.session_state.clear()
    self.mock_api_client.reset_mock()
```

### Async Issues
Use appropriate async test decorators if testing async functions:
```python
@patch('app.api_client')
async def test_async_function(self, mock_api):
    # Test async code
```