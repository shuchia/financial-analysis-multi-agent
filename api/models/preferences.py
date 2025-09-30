"""
Enhanced user preferences models for young investor features.
"""

from pydantic import BaseModel, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class AgeRange(str, Enum):
    """Age range categories."""
    HIGH_SCHOOL = "16-20 (High school/Early college)"
    COLLEGE = "21-25 (College/Entry career)"
    EARLY_CAREER = "26-30 (Early career)"
    ESTABLISHING = "31-35 (Establishing career)"
    EXPERIENCED = "36+ (Experienced)"


class IncomeRange(str, Enum):
    """Income range categories."""
    STUDENT = "Student/No income"
    LOW = "$0-25k"
    MEDIUM_LOW = "$25k-50k"
    MEDIUM_HIGH = "$50k-75k"
    HIGH = "$75k+"


class InvestmentGoal(str, Enum):
    """Primary investment goals."""
    LEARN = "Learn investing basics"
    EMERGENCY_FUND = "Build emergency fund"
    MAJOR_PURCHASE = "Save for a major purchase"
    LONG_TERM_WEALTH = "Long-term wealth building"
    RETIREMENT = "Retirement planning"
    SIDE_INCOME = "Generate side income"


class Timeline(str, Enum):
    """Investment timeline categories."""
    LEARNING = "Learning only (no timeline)"
    SHORT = "1-2 years"
    MEDIUM = "3-5 years"
    LONG = "5-10 years"
    VERY_LONG = "10+ years"


class RiskProfile(str, Enum):
    """Risk tolerance profiles."""
    CONSERVATIVE = "Conservative"
    MODERATE = "Moderate"
    GROWTH_ORIENTED = "Growth-Oriented"
    AGGRESSIVE = "Aggressive"


class Demographics(BaseModel):
    """User demographics information."""
    age_range: AgeRange
    income_range: IncomeRange


class InvestmentGoals(BaseModel):
    """Investment goals and objectives."""
    primary_goal: InvestmentGoal
    timeline: Timeline


class ScenarioResponse(BaseModel):
    """Individual scenario response."""
    scenario_id: str
    response: str
    score: int


class RiskAssessment(BaseModel):
    """Scenario-based risk assessment."""
    risk_score: int
    risk_profile: RiskProfile
    scenario_responses: Dict[str, str]  # scenario_id -> response
    
    @validator('risk_score')
    def validate_risk_score(cls, v):
        if not 3 <= v <= 12:  # 3 scenarios * 1-4 points each
            raise ValueError('Risk score must be between 3 and 12')
        return v


class FinancialStatus(BaseModel):
    """Financial status and investment capacity."""
    initial_amount: str
    has_emergency_fund: bool


class TutorialPreferences(BaseModel):
    """Tutorial and learning preferences."""
    tutorial_stock: Optional[str] = None
    suggested_stocks: Dict[str, str] = {}  # symbol -> description
    tutorial_completed: bool = False


class Achievement(BaseModel):
    """Individual achievement."""
    id: str
    name: str
    description: str
    unlocked_at: Optional[datetime] = None
    progress: Dict[str, Any] = {}


class Achievements(BaseModel):
    """Achievement tracking."""
    unlocked: List[str] = []  # List of achievement IDs
    progress: Dict[str, Any] = {}  # achievement_id -> progress data


class AnalysisPreferences(BaseModel):
    """Analysis and display preferences."""
    default_depth: str = "standard"
    show_tooltips: bool = True
    show_educational_content: bool = True
    preferred_chart_type: str = "candlestick"


class EnhancedUserPreferences(BaseModel):
    """Enhanced user preferences structure."""
    demographics: Demographics
    investment_goals: InvestmentGoals
    risk_assessment: RiskAssessment
    financial_status: FinancialStatus
    tutorial_preferences: TutorialPreferences
    achievements: Achievements
    analysis_preferences: AnalysisPreferences = AnalysisPreferences()
    onboarding_completed_at: datetime
    last_updated: datetime = datetime.utcnow()
    
    class Config:
        use_enum_values = True


class PreferencesUpdate(BaseModel):
    """Model for updating preferences."""
    demographics: Optional[Demographics] = None
    investment_goals: Optional[InvestmentGoals] = None
    risk_assessment: Optional[RiskAssessment] = None
    financial_status: Optional[FinancialStatus] = None
    tutorial_preferences: Optional[TutorialPreferences] = None
    achievements: Optional[Achievements] = None
    analysis_preferences: Optional[AnalysisPreferences] = None
    
    class Config:
        use_enum_values = True


# Legacy preferences support for backward compatibility
class LegacyPreferences(BaseModel):
    """Legacy preferences structure for backward compatibility."""
    experience: Optional[str] = None
    goals: Optional[List[str]] = None
    risk_tolerance: Optional[int] = None
    initial_amount: Optional[str] = None
    timestamp: Optional[str] = None


def migrate_legacy_preferences(legacy_prefs: Dict[str, Any]) -> EnhancedUserPreferences:
    """Migrate legacy preferences to enhanced structure."""
    
    # Map legacy experience to age range (best guess)
    experience_to_age = {
        "Complete beginner 🌱": AgeRange.HIGH_SCHOOL,
        "Some knowledge 📚": AgeRange.COLLEGE,
        "Intermediate 📈": AgeRange.EARLY_CAREER,
        "Advanced 🚀": AgeRange.EXPERIENCED
    }
    
    # Map legacy goals to primary goal (pick first one)
    goals_mapping = {
        "Learn about investing": InvestmentGoal.LEARN,
        "Build long-term wealth": InvestmentGoal.LONG_TERM_WEALTH,
        "Generate passive income": InvestmentGoal.SIDE_INCOME,
        "Save for retirement": InvestmentGoal.RETIREMENT,
        "Short-term trading": InvestmentGoal.MAJOR_PURCHASE,
        "Understand my employer's stock": InvestmentGoal.LEARN
    }
    
    # Map amount to income range (rough estimation)
    amount_to_income = {
        "$0-100": IncomeRange.STUDENT,
        "$100-500": IncomeRange.LOW,
        "$500-1,000": IncomeRange.MEDIUM_LOW,
        "$1,000-5,000": IncomeRange.MEDIUM_HIGH,
        "$5,000+": IncomeRange.HIGH
    }
    
    # Default values
    age_range = AgeRange.COLLEGE
    income_range = IncomeRange.MEDIUM_LOW
    primary_goal = InvestmentGoal.LEARN
    
    # Extract legacy data
    if 'experience' in legacy_prefs:
        age_range = experience_to_age.get(legacy_prefs['experience'], AgeRange.COLLEGE)
    
    if 'initial_amount' in legacy_prefs:
        income_range = amount_to_income.get(legacy_prefs['initial_amount'], IncomeRange.MEDIUM_LOW)
    
    if 'goals' in legacy_prefs and legacy_prefs['goals']:
        first_goal = legacy_prefs['goals'][0] if isinstance(legacy_prefs['goals'], list) else legacy_prefs['goals']
        primary_goal = goals_mapping.get(first_goal, InvestmentGoal.LEARN)
    
    # Map risk tolerance to risk profile
    risk_tolerance = legacy_prefs.get('risk_tolerance', 5)
    if risk_tolerance <= 3:
        risk_profile = RiskProfile.CONSERVATIVE
    elif risk_tolerance <= 6:
        risk_profile = RiskProfile.MODERATE
    elif risk_tolerance <= 8:
        risk_profile = RiskProfile.GROWTH_ORIENTED
    else:
        risk_profile = RiskProfile.AGGRESSIVE
    
    # Create enhanced preferences
    return EnhancedUserPreferences(
        demographics=Demographics(
            age_range=age_range,
            income_range=income_range
        ),
        investment_goals=InvestmentGoals(
            primary_goal=primary_goal,
            timeline=Timeline.LONG
        ),
        risk_assessment=RiskAssessment(
            risk_score=max(3, min(12, risk_tolerance + 3)),  # Convert 1-10 to 3-12
            risk_profile=risk_profile,
            scenario_responses={}
        ),
        financial_status=FinancialStatus(
            initial_amount=legacy_prefs.get('initial_amount', '$100-500'),
            has_emergency_fund=False
        ),
        tutorial_preferences=TutorialPreferences(),
        achievements=Achievements(),
        onboarding_completed_at=datetime.fromisoformat(legacy_prefs.get('timestamp', datetime.utcnow().isoformat()))
    )


def get_achievement_definitions() -> Dict[str, Achievement]:
    """Get all available achievement definitions."""
    return {
        'first_analysis': Achievement(
            id='first_analysis',
            name='Knowledge Seeker',
            description='Complete your first stock analysis'
        ),
        'five_analyses': Achievement(
            id='five_analyses',
            name='Market Explorer',
            description='Analyze 5 different companies'
        ),
        'first_watchlist': Achievement(
            id='first_watchlist',
            name='Wise Investor',
            description='Create your first watchlist'
        ),
        'portfolio_tracking': Achievement(
            id='portfolio_tracking',
            name='Portfolio Builder',
            description='Track your investment performance'
        ),
        'long_term_hold': Achievement(
            id='long_term_hold',
            name='Long-term Thinker',
            description='Hold an analysis for 30+ days'
        ),
        'risk_assessment': Achievement(
            id='risk_assessment',
            name='Risk Aware',
            description='Complete detailed risk assessment'
        ),
        'tutorial_master': Achievement(
            id='tutorial_master',
            name='Tutorial Master',
            description='Complete all tutorial modules'
        ),
        'consistent_learner': Achievement(
            id='consistent_learner',
            name='Consistent Learner',
            description='Use the platform for 7 consecutive days'
        )
    }