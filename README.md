# Financial Analysis: Multi-Agent Open Source LLM

An advanced stock analysis tool powered by AI agents that provides comprehensive financial analysis using open-source language models. This application combines technical analysis, fundamental analysis, and sentiment analysis to deliver detailed insights for stock market investments.

## Features

- Real-time stock data analysis
- Technical analysis with chart pattern recognition
- Fundamental analysis of company financials
- Market sentiment analysis
- Risk assessment
- Competitor analysis
- Investment strategy recommendations
- Interactive charts and visualizations

## Installation

1. Clone the repository:
```bash
git clone https://github.com/imanoop7/Financial-Analysis--Multi-Agent-Open-Source-LLM
cd Financial-Analysis--Multi-Agent-Open-Source-LLM
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Make sure you have Ollama installed and running on your system. Visit [Ollama's website](https://ollama.ai/) for installation instructions.

## Usage

1. Start the application:
```bash
streamlit run app.py
```

2. Enter a stock symbol (e.g., AAPL for Apple Inc.) in the input field.

3. Click "Analyze Stock" to generate a comprehensive analysis report.

The application will display:
- Technical analysis insights
- Chart patterns
- Fundamental analysis
- Market sentiment
- Risk assessment
- Competitor analysis
- Investment strategy recommendations

## Dependencies

- crewai - For multi-agent orchestration
- langchain - For LLM interactions
- ollama - For running local LLMs
- yfinance - For fetching stock data
- streamlit - For the web interface
- plotly - For interactive charts
- And other data analysis libraries

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.