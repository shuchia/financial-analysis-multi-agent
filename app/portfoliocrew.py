from crewai import Agent, Task, Crew, Process, LLM
from tools.yf_tech_analysis_tool import yf_tech_analysis
from tools.yf_fundamental_analysis_tool import yf_fundamental_analysis
from tools.sentiment_analysis_tool import sentiment_analysis
from tools.competitor_analysis_tool import competitor_analysis
from tools.risk_assessment_tool import risk_assessment
from tools.fractional_share_tool import calculate_fractional_shares, get_fractional_portfolio_suggestions
import logging
import time
import os

def create_crew(amount,user_profile=None):
    # Configure logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Set default user profile if none provided
    if user_profile is None:
        user_profile = {
            'age_range': '25-35',
            'income_range': '50k-100k',
            'primary_goal': 'wealth_building',
            'timeline': '5-10 years',
            'risk_profile': 'moderate',
            'experience': 'beginner'
        }
    
    logger.info(f"Creating portfolio crew for  user profile: {user_profile.get('age_range', 'unknown')} years old, {user_profile.get('experience', 'unknown')} experience")
    
    # Initialize AWS Bedrock LLM using CrewAI's LLM class
    # In ECS Fargate, credentials are automatically obtained from the task role
    llm = LLM(
        model="anthropic.claude-3-haiku-20240307-v1:0",
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    logger.debug("AWS Bedrock LLM initialized successfully")

    # Define Agents
    logger.info("Creating agents...")

    strategist = Agent(
        role='Portfolio Strategist',
        goal='Create personalized investment portfolios optimized for user risk tolerance, investment amount, and goals',
        backstory="""You are an expert portfolio manager who specializes in 
                    creating starter portfolios for young investors. You understand modern 
                    portfolio theory, risk management, and behavioral finance. You excel at 
                    translating complex allocation strategies into simple, actionable portfolios 
                    that beginners can understand and implement. You always consider the user's 
                    age, timeline, emergency fund status, and risk tolerance when making 
                    recommendations.""",
        tools=[],
        llm=llm,
        verbose=True
    )
    logger.debug("Portfolio Strategist agent created")

    # Define Tasks
    logger.info("Creating tasks...")
    
    portfolio_task = Task(
        description=f""" Create a diversified portfolio for this investor: PROFILE: - Age: {user_profile.get('age_range', '25-35')} - Risk tolerance: 
                             {user_profile.get('risk_profile', 'moderate')} {user_profile.get('risk_score')}- Amount: ${amount} - Timeline: {user_profile.get('timeline', '5-10 years')} - 
                             Goal: {user_profile.get('primary_goal', 'wealth_building')} - Emergency Fund: {user_profile.get('emergency_fund_status', 'Getting there')} 
                             REQUIREMENTS: 1. Suggest {get_position_count(amount)} positions maximum 2. Use primarily ETFs for diversification 
                             3. Can include 1-2 individual stocks if amount > $500 4. Match risk tolerance exactly SPECIFY FOR EACH HOLDING: - 
                             Ticker symbol - Allocation percentage - Category (Core/Satellite/Stock) - Investment thesis (one line) RISK GUIDELINES: - 
                             Conservative: 60% bonds, 40% stocks - Moderate: 30% bonds, 70% stocks - Aggressive: 10% bonds, 90% stocks 
                             OUTPUT FORMAT: Return a portfolio with specific tickers and allocations. Example: VOO: 40% - 
                             Core US equity exposure VXUS: 20% - International diversification BND: 30% - Fixed income stability QQQ: 
                             10% - Tech growth exposure Expected Annual Return: X-Y% Portfolio Risk: Low/Medium/High """,
        agent=strategist,
        expected_output="Portfolio with specific tickers and percentages",
        max_retries=1
    )
    logger.debug("Portfolio task created")

    market_analysis_task = Task(
        description=f"""
                    Analyze current market conditions for portfolio creation:
                    1. Overall market sentiment (bullish/bearish/neutral)
                    2. Sector performance and trends
                    3. Interest rate environment
                    4. Volatility levels (VIX)
                    5. Recommended asset classes for current conditions

                    Consider this is for a {user_profile.get('age_range', '25-35')} year old 
                    with {user_profile.get('risk_profile', 'moderate')} risk tolerance.
                    """,
        agent=strategist,
        expected_output="Market analysis with conditions affecting portfolio allocation",
        max_retries=1
    )
    logger.debug("Market analysis task created")


    # Create Crew
    logger.info("Creating portfolio crew with sequential process...")
    crew = Crew(
        agents=[ strategist],
        tasks=[portfolio_task],
        process=Process.sequential
    )
    logger.info("Portfolio Crew created successfully")

    return crew

def get_position_count(amount):
    # Convert amount string to number if needed
    if isinstance(amount, str):
        # Extract number from string like "$1,000" or "$1000"
        import re
        amount_match = re.search(r'[\d,]+', amount.replace('$', ''))
        if amount_match:
            amount = float(amount_match.group().replace(',', ''))
        else:
            amount = 100  # Default fallback
    
    if amount < 50:
        return 1
    elif amount < 100:
        return 2
    elif amount < 500:
        return "3-4"
    elif amount < 1000:
        return "4-5"
    else:
        return "5-7"

def create_portfolio(amount, user_profile=None):
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting portfolio creation for {amount} with user profile: {user_profile.get('age_range', 'unknown') if user_profile else 'default'}")
    start_time = time.time()
    
    try:
        crew = create_crew(amount, user_profile)
        logger.info("Initiating crew kickoff...")
        
        # Track individual task progress
        logger.debug("=== CREW EXECUTION STARTED ===")
        logger.debug(f"Total agents: {len(crew.agents)}")
        logger.debug(f"Total tasks: {len(crew.tasks)}")
        
        for i, task in enumerate(crew.tasks, 1):
            logger.debug(f"Task {i}/{len(crew.tasks)}: {task.description[:100]}...")
            logger.debug(f"Assigned to agent: {task.agent.role}")
        
        logger.info("Beginning sequential task execution...")
        result = crew.kickoff()
        
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"=== CREW EXECUTION COMPLETED ===")
        logger.info(f"Analysis completed successfully in {execution_time:.2f} seconds")
        logger.debug(f"Result type: {type(result)}")
        logger.debug(f"Result content: {result}")
        
        # Validate result is not None or empty
        if result is None:
            logger.error("Result is None")
            raise ValueError("Invalid response from LLM call - None or empty")
        
        if hasattr(result, 'tasks_output') and not result.tasks_output:
            logger.error("Result tasks_output is empty")
            raise ValueError("Invalid response from LLM call - None or empty")
        
        return result
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        logger.error(f"Analysis failed after {time.time() - start_time:.2f} seconds")
        raise
