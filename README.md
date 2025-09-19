# Financial Analysis: Multi-Agent System with AWS Bedrock

An advanced AI-powered stock analysis platform that leverages multi-agent architecture to provide comprehensive financial analysis. The application uses AWS Bedrock (Claude 3 Haiku) as the LLM backend and combines multiple specialized AI agents to deliver detailed investment insights.

## 🚀 Features

### Multi-Agent Architecture
- **Stock Market Researcher**: Gathers comprehensive market data using technical and fundamental analysis tools
- **Sentiment Analyst**: Analyzes market sentiment from news and social media
- **Financial Analyst**: Synthesizes data and conducts risk assessments
- **Investment Strategist**: Develops tailored investment strategies

### Analysis Capabilities
- **Technical Analysis**: Chart patterns, moving averages, RSI, MACD, and advanced indicators
- **Fundamental Analysis**: Financial ratios, company metrics, and valuation analysis
- **Sentiment Analysis**: News sentiment scoring and social media trends
- **Risk Assessment**: Comprehensive risk evaluation and scenario analysis
- **Competitor Analysis**: Comparative market analysis
- **Interactive Visualizations**: Real-time candlestick charts with technical indicators

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   CrewAI Agents  │    │  AWS Bedrock    │
│                 │◄──►│                  │◄──►│  Claude 3 Haiku │
│  - User Input   │    │  - Researcher    │    │                 │
│  - Visualizations│    │  - Analyst       │    └─────────────────┘
│  - Results      │    │  - Strategist    │           
└─────────────────┘    │  - Sentiment     │    ┌─────────────────┐
                       └──────────────────┘    │  Data Sources   │
                                 │             │                 │
                                 └────────────►│  - Yahoo Finance│
                                               │  - News APIs    │
                                               │  - Market Data  │
                                               └─────────────────┘
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.11+
- AWS Account with Bedrock access
- Git

### Local Development

1. **Clone the repository:**
```bash
git clone https://github.com/shuchia/financial-analysis-multi-agent.git
cd financial-analysis-multi-agent
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure AWS credentials:**
```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Option 2: AWS CLI configuration
aws configure
```

4. **Run the application:**
```bash
streamlit run app.py
```

5. **Access the app:**
   Open your browser to `http://localhost:8501`

### Environment Configuration

Create a `.env` file based on `.env.template`:
```bash
cp .env.template .env
# Edit .env with your AWS credentials
```

## ☁️ AWS App Runner Deployment

The application is configured for seamless deployment on AWS App Runner with automatic scaling and managed infrastructure.

### Quick Deploy
1. **Prepare AWS:**
   - Ensure AWS CLI is configured
   - Set up GitHub connection in App Runner console

2. **Deploy:**
```bash
./deploy.sh
```

3. **Manual Deployment:**
   - Go to [AWS App Runner Console](https://console.aws.amazon.com/apprunner/)
   - Create service from source code repository
   - Connect to this GitHub repository
   - App Runner will automatically use `apprunner.yaml` configuration

### Configuration Files
- `apprunner.yaml`: AWS App Runner service configuration
- `Dockerfile`: Container configuration optimized for cloud deployment
- `deploy.sh`: Deployment automation script
- `DEPLOYMENT.md`: Complete deployment guide

## 📊 Usage

1. **Enter Stock Symbol**: Input any valid stock ticker (e.g., AAPL, GOOGL, TSLA)
2. **Run Analysis**: Click "Analyze Stock" to start the multi-agent workflow
3. **Review Results**: The system will display:
   - Comprehensive AI analysis report
   - Interactive price charts with technical indicators
   - Key financial statistics and metrics
   - Investment recommendations

### Sample Analysis Output
The multi-agent system provides:
- **Technical Analysis**: RSI, MACD, moving averages, support/resistance levels
- **Fundamental Metrics**: P/E ratio, market cap, dividend yield, beta
- **Risk Assessment**: Volatility analysis and risk scoring
- **Market Sentiment**: News sentiment and social media trends
- **Investment Strategy**: Tailored recommendations for different investor profiles

## 🔧 Key Dependencies

### Core Framework
- **CrewAI**: Multi-agent orchestration and workflow management
- **LangChain**: LLM integration and chain operations
- **Streamlit**: Web application framework

### AI & Analysis
- **AWS Bedrock**: Claude 3 Haiku LLM backend
- **pandas-ta**: Technical analysis indicators
- **yfinance**: Real-time market data
- **scipy**: Statistical computations

### Visualization
- **Plotly**: Interactive charts and graphs
- **NumPy/Pandas**: Data manipulation and analysis

## 🧪 Local Testing

Test the Docker container locally:
```bash
# Build the image
docker build -t financial-analysis-app .

# Run locally
docker run -p 8080:8080 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e AWS_DEFAULT_REGION=us-east-1 \
  financial-analysis-app
```

## 📁 Project Structure

```
├── app.py                          # Main Streamlit application
├── crew.py                         # Multi-agent crew configuration
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Container configuration
├── apprunner.yaml                 # AWS App Runner config
├── deploy.sh                      # Deployment script
├── DEPLOYMENT.md                  # Deployment guide
├── .env.template                  # Environment variables template
├── .dockerignore                  # Docker build exclusions
└── tools/                         # Analysis tools
    ├── yf_tech_analysis_tool.py   # Technical analysis
    ├── yf_fundamental_analysis_tool.py # Fundamental analysis
    ├── sentiment_analysis_tool.py  # Sentiment analysis
    ├── competitor_analysis_tool.py # Competitor analysis
    └── risk_assessment_tool.py     # Risk assessment
```

## 🔒 Security & Best Practices

- Uses IAM roles for AWS access when deployed
- Non-root user in container for security
- Environment variable-based configuration
- Comprehensive health checks
- Optimized for production deployment

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 **Documentation**: See `DEPLOYMENT.md` for detailed deployment instructions
- 🐛 **Issues**: Report bugs via GitHub Issues
- 💡 **Feature Requests**: Submit enhancement requests via GitHub Issues

---

**Built with ❤️ using AWS Bedrock, CrewAI, and Streamlit**