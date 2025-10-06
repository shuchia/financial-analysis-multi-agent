# Test User Profiles for Portfolio Generation Testing

This document contains a comprehensive list of test user profiles designed to test all combinations of user profile elements in the InvestForge portfolio generation feature.

## Test User Profiles

### Young Investors (16-25 years)

#### Conservative Young Investors

1. **emma.conservative.student@test.com**
   - Age: 16-20 (High school/Early college)
   - Timeline: Learning only (no timeline)
   - Emergency Fund: Already have one
   - Investment Amount: $25 - Great starting point
   - Loss Reaction: Sell immediately

2. **alex.safe.college@test.com**
   - Age: 21-25 (College/Entry career)
   - Timeline: 1-2 years
   - Emergency Fund: Getting there
   - Investment Amount: $100 - Solid foundation
   - Loss Reaction: Panic and check constantly

#### Moderate Young Investors

3. **jordan.balanced.grad@test.com**
   - Age: 21-25 (College/Entry career)
   - Timeline: 3-5 years
   - Emergency Fund: Getting there
   - Investment Amount: $500 - Strong commitment
   - Loss Reaction: Feel worried but hold

4. **taylor.growth.youngpro@test.com**
   - Age: 21-25 (College/Entry career)
   - Timeline: 5-10 years
   - Emergency Fund: Already have one
   - Investment Amount: $1,000 - Advanced starter
   - Loss Reaction: Hold and wait it out

#### Aggressive Young Investors

5. **casey.aggressive.crypto@test.com**
   - Age: 16-20 (High school/Early college)
   - Timeline: 10+ years
   - Emergency Fund: Don't have one yet
   - Investment Amount: $250 - Getting serious
   - Loss Reaction: Buy more (opportunity!)

### Early Career (26-35 years)

#### Conservative Early Career

6. **mike.cautious.newjob@test.com**
   - Age: 26-30 (Early career)
   - Timeline: 1-2 years
   - Emergency Fund: Already have one
   - Investment Amount: $2,500 - Serious investor
   - Loss Reaction: Sell immediately

7. **sarah.stable.teacher@test.com**
   - Age: 31-35 (Establishing career)
   - Timeline: 3-5 years
   - Emergency Fund: Already have one
   - Investment Amount: $5,000 - Substantial start
   - Loss Reaction: Panic and check constantly

#### Moderate Early Career

8. **david.balanced.engineer@test.com**
   - Age: 26-30 (Early career)
   - Timeline: 5-10 years
   - Emergency Fund: Getting there
   - Investment Amount: $10,000 - Major commitment
   - Loss Reaction: Feel worried but hold

9. **lisa.moderate.manager@test.com**
   - Age: 31-35 (Establishing career)
   - Timeline: 10+ years
   - Emergency Fund: Getting there
   - Investment Amount: $25,000+ - High confidence
   - Loss Reaction: Hold and wait it out

#### Aggressive Early Career

10. **ryan.growth.startup@test.com**
    - Age: 26-30 (Early career)
    - Timeline: 10+ years
    - Emergency Fund: Don't have one yet
    - Investment Amount: $5,000 - Substantial start
    - Loss Reaction: Buy more (opportunity!)

### Experienced Investors (36+ years)

#### Conservative Experienced

11. **patricia.safe.executive@test.com**
    - Age: 36+ (Experienced)
    - Timeline: 1-2 years
    - Emergency Fund: Already have one
    - Investment Amount: $25,000+ - Experienced investor
    - Loss Reaction: Sell immediately

12. **robert.preservation.retiree@test.com**
    - Age: 36+ (Experienced)
    - Timeline: 3-5 years
    - Emergency Fund: Already have one
    - Investment Amount: $10,000 - Major commitment
    - Loss Reaction: Panic and check constantly

#### Moderate Experienced

13. **michelle.balanced.doctor@test.com**
    - Age: 36+ (Experienced)
    - Timeline: 5-10 years
    - Emergency Fund: Getting there
    - Investment Amount: $25,000+ - Experienced investor
    - Loss Reaction: Feel worried but hold

14. **james.steady.consultant@test.com**
    - Age: 36+ (Experienced)
    - Timeline: 10+ years
    - Emergency Fund: Already have one
    - Investment Amount: $5,000 - Substantial start
    - Loss Reaction: Hold and wait it out

#### Aggressive Experienced

15. **jennifer.risk.entrepreneur@test.com**
    - Age: 36+ (Experienced)
    - Timeline: 10+ years
    - Emergency Fund: Don't have one yet
    - Investment Amount: $25,000+ - Experienced investor
    - Loss Reaction: Buy more (opportunity!)

### Edge Cases & Special Scenarios

#### Minimum Investment

16. **penny.minimum.student@test.com**
    - Age: 16-20 (High school/Early college)
    - Timeline: Learning only (no timeline)
    - Emergency Fund: Don't have one yet
    - Investment Amount: $10 - Perfect for learning
    - Loss Reaction: Sell immediately

#### Maximum Investment

17. **max.wealthy.ceo@test.com**
    - Age: 36+ (Experienced)
    - Timeline: 10+ years
    - Emergency Fund: Already have one
    - Investment Amount: $25,000+ - Experienced investor
    - Loss Reaction: Buy more (opportunity!)

#### Learning Focus

18. **learning.curious.researcher@test.com**
    - Age: 26-30 (Early career)
    - Timeline: Learning only (no timeline)
    - Emergency Fund: Getting there
    - Investment Amount: $100 - Conservative start
    - Loss Reaction: Feel worried but hold

#### No Emergency Fund Risk

19. **risky.nofund.gambler@test.com**
    - Age: 31-35 (Establishing career)
    - Timeline: 5-10 years
    - Emergency Fund: Don't have one yet
    - Investment Amount: $2,500 - Serious investor
    - Loss Reaction: Buy more (opportunity!)

#### Short Timeline High Amount

20. **urgent.wealthy.investor@test.com**
    - Age: 36+ (Experienced)
    - Timeline: 1-2 years
    - Emergency Fund: Already have one
    - Investment Amount: $10,000 - Major commitment
    - Loss Reaction: Hold and wait it out

## Testing Matrix Coverage

- **Age Groups:** ✅ All 5 covered (16-20, 21-25, 26-30, 31-35, 36+)
- **Timelines:** ✅ All 5 covered (Learning, 1-2yr, 3-5yr, 5-10yr, 10+yr)
- **Emergency Fund:** ✅ All 3 covered (Don't have, Getting there, Already have)
- **Investment Amounts:** ✅ All ranges covered ($10 to $25,000+)
- **Risk Reactions:** ✅ All 5 covered (Sell, Panic, Worried, Hold, Buy more)

## Risk Profile Distribution

Based on the onboarding answers, these test users should result in:
- **Conservative (Low Risk):** Users 1, 2, 6, 7, 11, 12, 16
- **Moderate (Medium Risk):** Users 3, 4, 8, 9, 13, 14, 18, 20
- **Aggressive (High Risk):** Users 5, 10, 15, 17, 19

## Usage Instructions

1. Sign up with each test email address
2. Complete the onboarding flow with the specified profile attributes
3. Click "Generate My Portfolio" to test portfolio generation
4. Verify that the recommended portfolio matches the risk profile and investment amount
5. Document any issues or unexpected results

## Expected Portfolio Characteristics

### Conservative Portfolios (Risk Score < 0.3)
- 60% bonds, 40% stocks allocation
- Focus on BND, AGG, TLT for bonds
- Conservative equity ETFs like VIG, SCHD

### Moderate Portfolios (Risk Score 0.3-0.7)
- 30% bonds, 70% stocks allocation
- Mix of VOO, VTI for core equity
- Some international exposure with VXUS
- Balanced allocation

### Aggressive Portfolios (Risk Score > 0.7)
- 10% bonds, 90% stocks allocation
- Growth-focused ETFs like QQQ, VUG
- Individual stocks for amounts > $500
- Higher volatility tolerance