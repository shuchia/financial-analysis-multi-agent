import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
from crew import run_analysis
import json
import logging
import time

def main():
    # Configure logging for Streamlit app
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger = logging.getLogger(__name__)
    # Force HTTP polling instead of WebSocket
    st.set_page_config(
        page_title="AI-Powered Advanced Stock Analysis",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Add this at the top of your app
    if 'websocket_disabled' not in st.session_state:
        st.session_state.websocket_disabled = True
        st.experimental_rerun()

    # User input
    stock_symbol = st.text_input("Enter stock symbol (e.g., AAPL):", "AAPL")
    
    if st.button("Analyze Stock"):
        logger.info(f"=== ANALYSIS WORKFLOW STARTED ===")
        logger.info(f"User initiated analysis for stock: {stock_symbol}")
        logger.debug(f"Stock symbol validation: {stock_symbol.upper().strip()}")
        
        # Run CrewAI analysis
        with st.spinner("Performing comprehensive stock analysis..."):
            logger.info("Phase 1: Starting CrewAI multi-agent analysis...")
            logger.debug("Invoking run_analysis function from crew module")
            
            analysis_start_time = time.time()
            result = run_analysis(stock_symbol)
            analysis_end_time = time.time()
            
            logger.info(f"Phase 1: CrewAI analysis completed in {analysis_end_time - analysis_start_time:.2f} seconds")
            logger.debug(f"Analysis result size: {len(str(result)) if result else 0} characters")
        
        # Parse the result
        logger.info("Phase 2: Parsing analysis results...")
        try:
            # Debug the result object to understand its structure
            logger.debug(f"Result type: {type(result)}")
            logger.debug(f"Result attributes: {dir(result)}")
            
            # CrewAI returns a CrewOutput object, check for common attributes
            if hasattr(result, 'raw'):
                # CrewOutput has a 'raw' attribute containing the final output
                analysis_text = str(result.raw)
                logger.debug(f"Using result.raw: {len(analysis_text)} characters")
            elif hasattr(result, 'result'):
                # Some versions might use 'result' attribute
                analysis_text = str(result.result)
                logger.debug(f"Using result.result: {len(analysis_text)} characters")
            elif hasattr(result, 'output'):
                # Some versions might use 'output' attribute
                analysis_text = str(result.output)
                logger.debug(f"Using result.output: {len(analysis_text)} characters")
            else:
                # Fallback to string representation
                analysis_text = str(result)
                logger.debug(f"Using str(result): {len(analysis_text)} characters")
            
            # Try to parse as JSON if it looks like JSON
            analysis_text = analysis_text.strip()
            if analysis_text.startswith('{') and analysis_text.endswith('}'):
                try:
                    analysis = json.loads(analysis_text)
                    logger.debug(f"Successfully parsed JSON analysis with {len(analysis)} sections")
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parsing failed: {e}. Treating as raw text.")
                    analysis = {"raw_analysis": analysis_text}
                    logger.debug("Parsed as raw text analysis")
            else:
                # Handle raw text output
                analysis = {"raw_analysis": analysis_text}
                logger.debug("Parsed as raw text analysis")
                
        except Exception as e:
            logger.error(f"Failed to parse analysis result: {e}")
            st.error("Failed to parse analysis results")
            return
        
        # Display analysis result
        logger.info("Phase 3: Rendering analysis results in UI...")
        st.header("AI Analysis Report")
        
        # Check if we have structured JSON data or raw text
        if 'raw_analysis' in analysis:
            # Display raw text analysis
            st.markdown(analysis['raw_analysis'])
        else:
            # Display structured JSON analysis
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Technical Analysis")
                st.write(analysis.get('technical_analysis', 'No technical analysis available'))
                
                st.subheader("Chart Patterns")
                st.write(analysis.get('chart_patterns', 'No chart patterns identified'))
            
            with col2:
                st.subheader("Fundamental Analysis")
                st.write(analysis.get('fundamental_analysis', 'No fundamental analysis available'))
                
                st.subheader("Sentiment Analysis")
                st.write(analysis.get('sentiment_analysis', 'No sentiment analysis available'))
            
            st.subheader("Risk Assessment")
            st.write(analysis.get('risk_assessment', 'No risk assessment available'))
            
            st.subheader("Competitor Analysis")
            st.write(analysis.get('competitor_analysis', 'No competitor analysis available'))
            
            st.subheader("Investment Strategy")
            st.write(analysis.get('investment_strategy', 'No investment strategy available'))
        
        # Fetch stock data for chart
        logger.info("Phase 4: Fetching stock data for visualization...")
        logger.debug(f"Requesting 1-year historical data for {stock_symbol}")
        
        try:
            stock = yf.Ticker(stock_symbol)
            hist = stock.history(period="1y")
            logger.debug(f"Retrieved {len(hist)} data points for chart")
        except Exception as e:
            logger.error(f"Failed to fetch stock data: {e}")
            st.error("Failed to fetch stock data for visualization")
            return
        
        # Create interactive chart
        logger.info("Phase 5: Creating interactive stock chart...")
        try:
            fig = go.Figure()
            logger.debug("Adding candlestick chart...")
            fig.add_trace(go.Candlestick(x=hist.index,
                                         open=hist['Open'],
                                         high=hist['High'],
                                         low=hist['Low'],
                                         close=hist['Close'],
                                         name='Price'))
            
            # Add volume bars
            logger.debug("Adding volume bars...")
            fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name='Volume', yaxis='y2'))
            
            # Add moving averages
            logger.debug("Calculating and adding moving averages...")
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(window=50).mean(), name='50-day MA'))
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(window=200).mean(), name='200-day MA'))
            
            fig.update_layout(
                title=f"{stock_symbol} Stock Analysis",
                yaxis_title='Price',
                yaxis2=dict(title='Volume', overlaying='y', side='right'),
                xaxis_rangeslider_visible=False
            )
            
            logger.debug("Rendering chart in Streamlit...")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            logger.error(f"Failed to create chart: {e}")
            st.error("Failed to create stock chart")
        
        # Display key statistics
        logger.info("Phase 6: Displaying key financial statistics...")
        st.subheader("Key Statistics")
        try:
            info = stock.info
            logger.debug(f"Retrieved {len(info)} info fields from yfinance")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                market_cap = info.get('marketCap')
                market_cap_display = f"${market_cap:,}" if market_cap else "N/A"
                st.metric("Market Cap", market_cap_display)
                st.metric("P/E Ratio", round(info.get('trailingPE', 0), 2))
            with col2:
                st.metric("52 Week High", f"${info.get('fiftyTwoWeekHigh', 0):,.2f}")
                st.metric("52 Week Low", f"${info.get('fiftyTwoWeekLow', 0):,.2f}")
            with col3:
                st.metric("Dividend Yield", f"{info.get('dividendYield', 0):.2%}")
                st.metric("Beta", round(info.get('beta', 0), 2))
            
            logger.info("=== ANALYSIS WORKFLOW COMPLETED SUCCESSFULLY ===")
        except Exception as e:
            logger.error(f"Failed to display key statistics: {e}")
            st.error("Failed to load key statistics")

if __name__ == "__main__":
    main()
