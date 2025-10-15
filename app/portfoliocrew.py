from crewai import Agent, Task, Crew, Process, LLM
from tools.yf_tech_analysis_tool import yf_tech_analysis
from tools.yf_fundamental_analysis_tool import yf_fundamental_analysis
from tools.sentiment_analysis_tool import sentiment_analysis
from tools.competitor_analysis_tool import competitor_analysis
from tools.risk_assessment_tool import risk_assessment
from tools.fractional_share_tool import calculate_fractional_shares, get_fractional_portfolio_suggestions
from tools.performance_projection_tool import calculate_portfolio_projections
import logging
import time
import os


def parse_timeline_to_years(timeline: str) -> int:
    """Convert timeline string to years (middle of range)."""
    timeline_map = {
        "Learning only (no timeline)": 5,
        "1-2 years": 2,
        "3-5 years": 4,
        "5-10 years": 7,
        "10+ years": 15
    }
    return timeline_map.get(timeline, 7)


def create_initial_crew(amount,user_profile=None):
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

    # Convert amount to numeric if it's a string (for backward compatibility)
    if isinstance(amount, str):
        import re
        amount_match = re.search(r'[\d,]+', amount.replace('$', ''))
        if amount_match:
            amount_numeric = float(amount_match.group().replace(',', ''))
        else:
            amount_numeric = 100.0
    else:
        amount_numeric = float(amount)

    # Format amount for display
    amount_display = f"${amount_numeric:,.0f}"

    logger.info(f"Creating portfolio crew for {amount_display}, user profile: {user_profile.get('age_range', 'unknown')} years old, {user_profile.get('experience', 'unknown')} experience")
    
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
        backstory="""You are an expert portfolio manager who creates personalized
                    starter portfolios for individual investors. You understand modern
                    portfolio theory, risk management, and behavioral finance. You excel at
                    translating complex allocation strategies into simple, actionable portfolios
                    that beginners can understand and implement.

                    IMPORTANT: Always address the investor directly using 'you' and 'your'
                    instead of third person ('the investor', 'they', 'them'). For example:
                    - Use: "This portfolio will help YOU achieve your goals"
                    - NOT: "This portfolio will help the investor achieve their goals"

                    You consider their age, timeline, emergency fund status, and risk tolerance
                    when making recommendations.""",
        tools=[calculate_portfolio_projections],
        llm=llm,
        verbose=True
    )
    logger.debug("Portfolio Strategist agent created")


    # Define Tasks
    logger.info("Creating portfolio task...")
    
    portfolio_task = Task(
        description=f""" Create a diversified portfolio for this investor: PROFILE: - Age: {user_profile.get('age_range', '25-35')} - Risk tolerance:
                             {user_profile.get('risk_profile', 'moderate')} {user_profile.get('risk_score')}- Amount: {amount_display} - Timeline: {user_profile.get('timeline', '5-10 years')} -
                             Goal: {user_profile.get('primary_goal', 'wealth_building')} - Emergency Fund: {user_profile.get('emergency_fund_status', 'Getting there')}
                             REQUIREMENTS:
            1. Suggest specific ETFs/stocks with exact percentages
            2. Match the risk tolerance (don't exceed it)
            3. For {amount_display}, suggest {get_position_count(amount_numeric)} positions maximum
            4. Include dollar amounts for each holding
            5. Provide brief reasoning for each pick
            6. Use only ETFs and stocks available for fractional shares
            7. Minimize fees - prioritize low-cost index funds
            8. Consider tax efficiency if applicable
            9. Ensure proper diversification for the amount
            10. Address the investor directly as 'you/your' (never 'the investor/their')

            OUTPUT FORMAT:
            Provide a clear portfolio with each holding formatted as:
            TICKER (Category) - XX% ($X,XXX) - One-line reasoning

            For example:
            VTI (ETF) - 40% ($4,000) - Provides you with broad market exposure
            AAPL (Technology) - 15% ($1,500) - Gives you exposure to strong growth potential

            Categories should be one of: ETF, Technology, Healthcare, Financial, Consumer, Energy, Industrial, Real Estate, or specific fund types

            Then provide these additional sections using the exact headers shown:

            ## RISK MANAGEMENT
            Key Risks to Watch:
            - [List 3-5 specific risks based on THIS portfolio's actual composition, e.g., "Tech sector concentration (40% in NASDAQ) - vulnerable to sector rotation"]
            - [Not generic market risks, but specific to the holdings you chose]

            ## PERFORMANCE OUTLOOK
            Expected Annual Return: X-Y%

            Key Monitoring Points:
            - Rebalancing trigger: [Specify when to rebalance, e.g., "When any position drifts more than 5% from target allocation"]
            - Monitoring frequency: [Based on their timeline, e.g., "Quarterly review recommended for 5-10 year timeline"]
            - Volatility expectations: [Expected volatility range, e.g., "Moderate volatility (10-15% annual standard deviation)"]

            ## COST EFFICIENCY
            - [Specific expense ratios of the funds you chose, e.g., "VTI expense ratio: 0.03% - among the lowest available"]
            - [Tax efficiency considerations specific to these holdings, e.g., "ETF structure provides tax-efficient capital gains distribution"]
            - [Fee minimization strategy used, e.g., "All holdings available commission-free at major brokerages"]
            """,
        agent=strategist,
        expected_output="Portfolio with specific tickers, percentages, and structured insights sections",
        max_retries=1
    )
    logger.debug("Portfolio task created")

    # Projection task - calculate performance projections
    logger.info("Creating projection task...")

    # Parse timeline to years
    timeline_years = parse_timeline_to_years(user_profile.get('timeline', '5-10 years'))

    # Determine volatility based on risk profile
    risk_profile = user_profile.get('risk_profile', 'moderate').lower()
    volatility_map = {
        'conservative': 0.10,
        'moderate': 0.15,
        'aggressive': 0.20
    }
    annual_volatility = volatility_map.get(risk_profile, 0.15)

    projection_task = Task(
        description=f"""Calculate performance projections for the recommended portfolio.

        USE THE TOOL: calculate_portfolio_projections

        INPUTS:
        - investment_amount: {amount_numeric}
        - expected_annual_return: (Use the expected return range you provided in the portfolio task, take the midpoint and convert percentage to decimal, e.g., if 7-9%, use 0.08)
        - timeline_years: {timeline_years}
        - annual_volatility: {annual_volatility}

        TASK:
        1. Use the performance projection tool with the parameters above
        2. Explain the results to the investor in simple terms
        3. Address them directly as 'you' and 'your'
        4. Describe what the conservative, expected, and optimistic scenarios mean for THEM

        OUTPUT FORMAT:
        Based on your {user_profile.get('timeline', '5-10 years')} timeline, here's what you can expect:

        📊 Conservative Scenario: $X,XXX (if market underperforms)
        📊 Expected Scenario: $X,XXX (most likely outcome)
        📊 Optimistic Scenario: $X,XXX (if market outperforms)

        This means your {amount_display} investment could grow to $X,XXX over the timeline,
        giving you a total return of X%. [Add context about what this means for their goals]
        """,
        agent=strategist,
        expected_output="Performance projections with investor-friendly explanation",
        context=[portfolio_task]
    )
    logger.debug("Projection task created")

    # Create Crew
    logger.info("Creating portfolio crew with sequential process...")
    portfolio_creation_crew = Crew(
        agents=[strategist],
        tasks=[portfolio_task, projection_task],
        process=Process.sequential
    )
    logger.info("Portfolio Crew created successfully")

    return portfolio_creation_crew

def create_education_crew(amount, portfolio,user_profile=None):

    # Initialize AWS Bedrock LLM using CrewAI's LLM class
    # In ECS Fargate, credentials are automatically obtained from the task role
    llm = LLM(
        model="anthropic.claude-3-haiku-20240307-v1:0",
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    # Configure logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    logger.debug("AWS Bedrock LLM initialized successfully")

    education_specialist = Agent(
        role='Investment Educator',
        goal='Educate beginner investors about their portfolios and investment concepts',
        backstory="""You are a patient and knowledgeable investment educator who specializes
                    in teaching beginners. You explain complex investment concepts in simple, relatable terms
                    using everyday analogies. You never use jargon without explaining it first. You're
                    enthusiastic about helping young people start their investment journey and always
                    celebrate small victories. You provide actionable education tied to their specific
                    portfolio.""",
        tools=[],  # No tools needed, just explanation
        llm=llm,
        verbose=True
    )
    education_task = Task(description=f"""
            Create educational content for this beginner investor:
            
            THEIR PORTFOLIO:
            {portfolio}
            
            INVESTOR BACKGROUND:
            - Age: {user_profile.get('age_range', '25-35')}
            - Experience: Beginner
            - Goal: {user_profile.get('primary_goal', 'wealth_building')}
            
            EDUCATIONAL CONTENT NEEDED:
            1. Explain what each ETF is and why it's included
            2. Describe how the portfolio works together
            3. Explain key concepts (diversification, rebalancing, etc.)
            4. Provide 3 important things to monitor
            5. Suggest next learning steps
            6. Include encouraging message about starting investing
            
            Use simple language and relatable analogies. Make it exciting!
            Remember this might be their first investment ever.
            """,
            agent=education_specialist,
            expected_output="Comprehensive educational guide tailored to the portfolio"
                          )
    logger.debug("Education task created")
    # Create Crew
    logger.info("Creating portfolio crew with sequential process...")
    education_crew = Crew(
        agents=[education_specialist],
        tasks=[education_task],
        process=Process.sequential
    )
    logger.info("Education Crew created successfully")

    return education_crew


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
        portfolio_creation_crew = create_initial_crew(amount, user_profile)
        logger.info("Initiating initial crew kickoff...")
        
        # Track individual task progress
        logger.debug("=== CREW EXECUTION STARTED ===")
        logger.debug(f"Total agents: {len(portfolio_creation_crew.agents)}")
        logger.debug(f"Total tasks: {len(portfolio_creation_crew.tasks)}")
        
        for i, task in enumerate(portfolio_creation_crew.tasks, 1):
            logger.debug(f"Task {i}/{len(portfolio_creation_crew.tasks)}: {task.description[:100]}...")
            logger.debug(f"Assigned to agent: {task.agent.role}")
        
        logger.info("Beginning sequential task execution...")
        result = portfolio_creation_crew.kickoff()
        
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"=== CREW EXECUTION COMPLETED ===")
        logger.info(f"Initial portfolio completed successfully in {execution_time:.2f} seconds")
        logger.debug(f"Result type: {type(result)}")
        logger.debug(f"Result content: {result}")
        
        # Validate result is not None or empty
        if result is None:
            logger.error("Result is None")
            raise ValueError("Invalid response from LLM call - None or empty")
        
        if hasattr(result, 'tasks_output') and not result.tasks_output:
            logger.error("Result tasks_output is empty")
            raise ValueError("Invalid response from LLM call - None or empty")
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        logger.error(f"Analysis failed after {time.time() - start_time:.2f} seconds")
        raise
    return result

def create_education(amount, portfolio, user_profile=None):
    logger = logging.getLogger(__name__)
    start_time = time.time()
    try:
        education_crew = create_education_crew(amount, portfolio,user_profile)
        logger.info("Initiating education crew kickoff...")
        # Track individual task progress
        logger.debug("=== CREW EXECUTION STARTED ===")
        logger.debug(f"Total agents: {len(education_crew.agents)}")
        logger.debug(f"Total tasks: {len(education_crew.tasks)}")

        for i, task in enumerate(education_crew.tasks, 1):
            logger.debug(f"Task {i}/{len(education_crew.tasks)}: {task.description[:100]}...")
            logger.debug(f"Assigned to agent: {task.agent.role}")

        logger.info("Beginning sequential task execution...")
        education_content = education_crew.kickoff()

        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"=== CREW EXECUTION COMPLETED ===")
        logger.info(f"Education specialist completed successfully in {execution_time:.2f} seconds")
        logger.debug(f"Result type: {type(education_content)}")
        logger.debug(f"Result content: {education_content}")

        # Validate result is not None or empty
        if education_content is None:
            logger.error("Result is None")
            raise ValueError("Invalid response from LLM call - None or empty")

        if hasattr(education_content, 'tasks_output') and not education_content.tasks_output:
            logger.error("Result tasks_output is empty")
            raise ValueError("Invalid response from LLM call - None or empty")
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        logger.error(f"Analysis failed after {time.time() - start_time:.2f} seconds")
        raise
    return {
            'content': education_content,
            'key_concepts':extract_key_concepts(education_content),
            'action_items': extract_action_items(education_content)
        }

def extract_key_concepts(education_content: str) -> list:
    """
    Extract key concepts from education content
    """
    concepts = []
    keywords = ['diversification', 'rebalancing', 'risk', 'return', 'ETF', 'allocation']

    for keyword in keywords:
        if keyword.lower() in str(education_content).lower():
            concepts.append(keyword)

    return concepts


def extract_action_items(education_content: str) -> list:
    """
    Extract action items from education content
    """
    # Simplified extraction
    return [
        "Review portfolio quarterly",
        "Set up automatic investing",
        "Continue learning about investing",
        "Monitor but don't panic during volatility"
    ]
