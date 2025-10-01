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

def create_crew(stock_symbol, user_profile=None):
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
    
    logger.info(f"Creating crew for stock symbol: {stock_symbol} with user profile: {user_profile.get('age_range', 'unknown')} years old, {user_profile.get('experience', 'unknown')} experience")
    
    # Initialize AWS Bedrock LLM using CrewAI's LLM class
    # In ECS Fargate, credentials are automatically obtained from the task role
    llm = LLM(
        model="anthropic.claude-3-haiku-20240307-v1:0",
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    logger.debug("AWS Bedrock LLM initialized successfully")

    # Define Agents
    logger.info("Creating agents...")
    
    researcher = Agent(
        role='Stock Market Researcher',
        goal='Gather and analyze comprehensive data about the stock',
        backstory="You're an experienced stock market researcher with a keen eye for detail and a talent for uncovering hidden trends.",
        tools=[yf_tech_analysis, yf_fundamental_analysis, competitor_analysis],
        llm=llm
    )
    logger.debug("Stock Market Researcher agent created")

    analyst = Agent(
        role='Financial Analyst',
        goal='Analyze the gathered data and provide investment insights',
        backstory="You're a seasoned financial analyst known for your accurate predictions and ability to synthesize complex information.",
        tools=[yf_tech_analysis, yf_fundamental_analysis, risk_assessment],
        llm=llm
    )
    logger.debug("Financial Analyst agent created")

    sentiment_analyst = Agent(
        role='Sentiment Analyst',
        goal='Analyze market sentiment and its potential impact on the stock',
        backstory="You're an expert in behavioral finance and sentiment analysis, capable of gauging market emotions and their effects on stock performance.",
        tools=[sentiment_analysis],
        llm=llm
    )
    logger.debug("Sentiment Analyst agent created")

    strategist = Agent(
        role='Investment Strategist',
        goal='Develop a comprehensive investment strategy based on all available data',
        backstory="You're a renowned investment strategist known for creating tailored investment plans that balance risk and reward.",
        tools=[calculate_fractional_shares, get_fractional_portfolio_suggestions],
        llm=llm
    )
    logger.debug("Investment Strategist agent created")

    # Define Tasks
    logger.info("Creating tasks...")
    
    research_task = Task(
        description=f"""Research {stock_symbol} for a {user_profile.get('age_range', '25-35')} year old investor with {user_profile.get('experience', 'beginner')} experience level using advanced technical and fundamental analysis tools.
        
        Primary investment goal: {user_profile.get('primary_goal', 'wealth_building')}
        Investment timeline: {user_profile.get('timeline', '5-10 years')}
        Income range: {user_profile.get('income_range', '50k-100k')}
        
        Focus your research on:
        - Key metrics most relevant to {user_profile.get('primary_goal', 'wealth_building')} goals
        - Financial ratios appropriate for {user_profile.get('timeline', 'medium-term')} investment horizon
        - Competitor analysis within their likely portfolio size range
        - Technical patterns suitable for {user_profile.get('experience', 'beginner')} level understanding
        
        Adjust explanation complexity for {user_profile.get('experience', 'beginner')} investor level.""",
        agent=researcher,
        expected_output=f"A comprehensive research report with technical analysis, fundamental metrics, chart patterns, and competitor analysis data tailored for {user_profile.get('experience', 'beginner')} investors focused on {user_profile.get('primary_goal', 'wealth_building')} with clear explanations and relevant metrics",
        max_retries=1
    )
    logger.debug("Research task created")

    sentiment_task = Task(
        description=f"""Analyze market sentiment for {stock_symbol} using news and social media data. Evaluate how current sentiment might affect the stock's performance considering the investor profile:
        
        Investor characteristics:
        - Age range: {user_profile.get('age_range', '25-35')}
        - Risk tolerance: {user_profile.get('risk_profile', 'moderate')}
        - Investment timeline: {user_profile.get('timeline', '5-10 years')}
        - Primary goal: {user_profile.get('primary_goal', 'wealth_building')}
        
        Focus sentiment analysis on:
        - News and events most relevant to {user_profile.get('timeline', 'medium-term')} investors
        - Sentiment factors that align with {user_profile.get('risk_profile', 'moderate')} risk tolerance
        - Social media trends relevant to {user_profile.get('age_range', '25-35')} demographic
        - Market emotion impacts on {user_profile.get('primary_goal', 'wealth_building')} strategies
        
        Filter out noise and focus on sentiment drivers that matter for this investor profile.""",
        agent=sentiment_analyst,
        expected_output=f"Sentiment analysis report with news sentiment scores, social media trends, and impact assessment on stock performance focused on factors relevant to {user_profile.get('risk_profile', 'moderate')} risk {user_profile.get('timeline', 'medium-term')} investors pursuing {user_profile.get('primary_goal', 'wealth_building')}",
        max_retries=1
    )
    logger.debug("Sentiment task created")

    analysis_task = Task(
        description=f"""Synthesize research and sentiment data for {stock_symbol} tailored to this investor profile:
        
        Investor Profile:
        - Age: {user_profile.get('age_range', '25-35')} | Experience: {user_profile.get('experience', 'beginner')}
        - Income: {user_profile.get('income_range', '50k-100k')} | Risk tolerance: {user_profile.get('risk_profile', 'moderate')}
        - Goal: {user_profile.get('primary_goal', 'wealth_building')} | Timeline: {user_profile.get('timeline', '5-10 years')}
        
        Tailor your analysis to:
        - Risk assessment appropriate for {user_profile.get('risk_profile', 'moderate')} risk tolerance
        - Financial metrics most important for {user_profile.get('primary_goal', 'wealth_building')} objectives
        - Valuation analysis suitable for {user_profile.get('timeline', 'medium-term')} holding period
        - Position sizing recommendations based on {user_profile.get('income_range', '50k-100k')} income level
        - Explanation style appropriate for {user_profile.get('experience', 'beginner')} experience level
        
        Emphasize analysis points most relevant to their investment profile and goals.""",
        agent=analyst,
        expected_output=f" A comprehensive financial analysis report with risk assessment, stock potential evaluation, and synthesis of all research data  customized for {user_profile.get('experience', 'beginner')} {user_profile.get('risk_profile', 'moderate')}-risk investor focused on {user_profile.get('primary_goal', 'wealth_building')}",
        max_retries=1
    )
    logger.debug("Analysis task created")

    # Determine if fractional shares should be considered based on user profile
    income_range = user_profile.get('income_range', '50k-100k')
    age_range = user_profile.get('age_range', '25-35')
    is_young_investor = any(age in age_range for age in ['16-20', '21-25', '26-30'])
    is_lower_income = any(income in income_range for income in ['under-25k', '25k-50k'])
    
    fractional_context = ""
    if is_young_investor or is_lower_income or user_profile.get('experience') == 'beginner':
        fractional_context = f"""
        
        IMPORTANT: Given this investor's profile, strongly consider fractional share investing options:
        - Use the calculate_fractional_shares tool to determine exact fractional positions for different investment amounts
        - Consider fractional shares if the stock price is high relative to their likely investment amount
        - Use get_fractional_portfolio_suggestions tool to create diversified portfolios with small amounts
        - Provide specific fractional share recommendations and calculations where appropriate
        - Explain how fractional shares make expensive stocks accessible with small investments
        """
    
    strategy_task = Task(
        description=f"""Based on all the gathered information about {stock_symbol} , develop a personalized investment strategy for {stock_symbol} based on this specific investor profile:
        
        Target Investor:
        - Demographics: {user_profile.get('age_range', '25-35')} years old, {user_profile.get('income_range', '50k-100k')} income
        - Investment experience: {user_profile.get('experience', 'beginner')} level
        - Risk profile: {user_profile.get('risk_profile', 'moderate')} risk tolerance
        - Primary goal: {user_profile.get('primary_goal', 'wealth_building')}
        - Investment timeline: {user_profile.get('timeline', '5-10 years')}
        
        Create strategy recommendations that:
        - Align with {user_profile.get('primary_goal', 'wealth_building')} investment objectives
        - Match {user_profile.get('risk_profile', 'moderate')} risk comfort level
        - Are appropriate for {user_profile.get('timeline', 'medium-term')} time horizon
        - Consider {user_profile.get('income_range', '50k-100k')} capital constraints
        - Provide clear action steps for {user_profile.get('experience', 'beginner')} experience level
        {fractional_context}
        
        Include specific position sizing, entry/exit strategies, and risk management tailored to this profile.""",
        agent=strategist,
        expected_output=f"Personalized investment strategy for {user_profile.get('age_range', '25-35')} year old {user_profile.get('experience', 'beginner')} investor pursuing {user_profile.get('primary_goal', 'wealth_building')} with actionable steps, risk-reward scenarios and tailored advice",
        max_retries=1
    )
    logger.debug("Strategy task created")

    # Create Crew
    logger.info("Creating crew with sequential process...")
    crew = Crew(
        agents=[researcher, sentiment_analyst, analyst, strategist],
        tasks=[research_task, sentiment_task, analysis_task, strategy_task],
        process=Process.sequential
    )
    logger.info("Crew created successfully")

    return crew

def run_analysis(stock_symbol, user_profile=None):
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting analysis for {stock_symbol} with user profile: {user_profile.get('age_range', 'unknown') if user_profile else 'default'}")
    start_time = time.time()
    
    try:
        crew = create_crew(stock_symbol, user_profile)
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
