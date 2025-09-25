from crewai import Agent, Task, Crew, Process, LLM
from tools.yf_tech_analysis_tool import yf_tech_analysis
from tools.yf_fundamental_analysis_tool import yf_fundamental_analysis
from tools.sentiment_analysis_tool import sentiment_analysis
from tools.competitor_analysis_tool import competitor_analysis
from tools.risk_assessment_tool import risk_assessment
import logging
import time
import os

def create_crew(stock_symbol):
    # Configure logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info(f"Creating crew for stock symbol: {stock_symbol}")
    
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
        tools=[],
        llm=llm
    )
    logger.debug("Investment Strategist agent created")

    # Define Tasks
    logger.info("Creating tasks...")
    
    research_task = Task(
        description=f"Research {stock_symbol} using advanced technical and fundamental analysis tools. Provide a comprehensive summary of key metrics, including chart patterns, financial ratios, and competitor analysis.",
        agent=researcher,
        expected_output="A comprehensive research report with technical analysis, fundamental metrics, chart patterns, and competitor analysis data",
        max_retries=1
    )
    logger.debug("Research task created")

    sentiment_task = Task(
        description=f"Analyze the market sentiment for {stock_symbol} using news and social media data. Evaluate how current sentiment might affect the stock's performance.",
        agent=sentiment_analyst,
        expected_output="A sentiment analysis report with news sentiment scores, social media trends, and impact assessment on stock performance",
        max_retries=1
    )
    logger.debug("Sentiment task created")

    analysis_task = Task(
        description=f"Synthesize the research data and sentiment analysis for {stock_symbol}. Conduct a thorough risk assessment and provide a detailed analysis of the stock's potential.",
        agent=analyst,
        expected_output="A comprehensive financial analysis report with risk assessment, stock potential evaluation, and synthesis of all research data",
        max_retries=1
    )
    logger.debug("Analysis task created")

    strategy_task = Task(
        description=f"Based on all the gathered information about {stock_symbol}, develop a comprehensive investment strategy. Consider various scenarios and provide actionable recommendations for different investor profiles.",
        agent=strategist,
        expected_output="A detailed investment strategy with actionable recommendations, risk-reward scenarios, and tailored advice for different investor profiles",
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

def run_analysis(stock_symbol):
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting analysis for {stock_symbol}")
    start_time = time.time()
    
    try:
        crew = create_crew(stock_symbol)
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
