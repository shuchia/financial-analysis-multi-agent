# InvestForge.io: AI-Powered Financial Analysis Platform

🚀 **Live at: [https://investforge.io](https://investforge.io)**

An advanced AI-powered stock analysis platform that leverages multi-agent architecture to provide comprehensive financial analysis. The application uses AWS Bedrock (Claude 3 Haiku) as the LLM backend and combines multiple specialized AI agents to deliver detailed investment insights.

Built with enterprise-grade AWS infrastructure, featuring automatic scaling, SSL encryption, and professional security measures.

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

## ☁️ Production AWS Deployment

**InvestForge.io** is deployed on enterprise-grade AWS infrastructure with comprehensive security and monitoring.

### Live Application
- **URL**: [https://investforge.io](https://investforge.io)
- **SSL**: AWS Certificate Manager (ACM) with automatic renewal
- **CDN**: CloudFront distribution for global performance
- **Security**: WAF protection, security groups, and encrypted connections

### Architecture Overview
```
Internet → Route 53 DNS → Application Load Balancer (HTTPS) → ECS Fargate → Streamlit App
             ↓                      ↓                           ↓
        SSL Certificate        WAF Protection            Auto-scaling Containers
        (AWS ACM)             (DDoS/Security)           (1-10 instances)
```

### Infrastructure Components
- **Domain**: `investforge.io` with Route 53 DNS management
- **Load Balancer**: Application Load Balancer with SSL termination
- **Compute**: ECS Fargate containers (1024 CPU, 2048 MB RAM)
- **Registry**: Amazon ECR for container images
- **Security**: AWS WAF, Security Groups, IAM roles
- **Monitoring**: CloudWatch logs and metrics
- **Secrets**: AWS Secrets Manager for configuration

### Local Development Setup
Follow the installation steps below to run the application locally for development and testing.

## 📊 Usage

### Quick Start
1. **Visit**: [https://investforge.io](https://investforge.io)
2. **Enter Stock Symbol**: Input any valid stock ticker (e.g., AAPL, GOOGL, TSLA)
3. **Run Analysis**: Click "Analyze Stock" to start the multi-agent workflow
4. **Review Results**: The system will display:
   - Comprehensive AI analysis report
   - Interactive price charts with technical indicators
   - Key financial statistics and metrics
   - Investment recommendations

### Local Development
1. **Clone & Setup**: Follow installation steps above
2. **Run Locally**: `streamlit run app.py`
3. **Access**: Open `http://localhost:8501`

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

## 🔒 Security & Production Features

### Security Measures
- **HTTPS Only**: SSL/TLS encryption with AWS Certificate Manager
- **WAF Protection**: Web Application Firewall blocking malicious requests
- **Network Security**: Private security groups and least-privilege access
- **IAM Roles**: Secure AWS service access without hardcoded credentials
- **Secrets Management**: AWS Secrets Manager for sensitive configuration
- **Container Security**: Non-root user and vulnerability scanning

### Production Capabilities
- **Auto-scaling**: ECS Fargate scales containers based on demand
- **High Availability**: Multi-AZ deployment with load balancing
- **Monitoring**: CloudWatch metrics, logs, and alerting
- **Cost Tracking**: Resource tagging for billing separation
- **Automated Deployment**: CI/CD with AWS CodeBuild and ECR
- **Health Checks**: Application and infrastructure health monitoring

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