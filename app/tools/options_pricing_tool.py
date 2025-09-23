from scipy.stats import norm


class OptionsPricingTool(BaseTool):
    name: str = "options_pricing"
    description: str = """
    Calculates options prices using Black-Scholes model and Greeks.
    Provides theoretical values and sensitivity measures.
    """

    def _run(self, ticker: str, strike_price: float, expiry_days: int,
             option_type: str = "call", risk_free_rate: float = 0.05) -> Dict:
        """Calculate option price and Greeks."""

        # Get current stock data
        stock = yf.Ticker(ticker)
        current_price = stock.history(period="1d")['Close'].iloc[-1]

        # Calculate historical volatility
        hist_data = stock.history(period="1y")['Close']
        returns = hist_data.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # Annualized

        # Time to expiry in years
        T = expiry_days / 365

        # Black-Scholes calculation
        def black_scholes(S, K, T, r, sigma, option_type="call"):
            d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)

            if option_type == "call":
                price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            else:
                price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

            return price, d1, d2

        # Calculate option price
        option_price, d1, d2 = black_scholes(current_price, strike_price, T,
                                             risk_free_rate, volatility, option_type)

        # Calculate Greeks
        def calculate_greeks(S, K, T, r, sigma, d1, d2, option_type="call"):
            # Delta: Rate of change of option price with respect to stock price
            if option_type == "call":
                delta = norm.cdf(d1)
            else:
                delta = -norm.cdf(-d1)

            # Gamma: Rate of change of delta
            gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))

            # Theta: Rate of change with respect to time (daily)
            if option_type == "call":
                theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
                         - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
            else:
                theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
                         + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365

            # Vega: Rate of change with respect to volatility
            vega = S * norm.pdf(d1) * np.sqrt(T) / 100

            # Rho: Rate of change with respect to interest rate
            if option_type == "call":
                rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
            else:
                rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100

            return delta, gamma, theta, vega, rho

        delta, gamma, theta, vega, rho = calculate_greeks(current_price, strike_price,
                                                          T, risk_free_rate, volatility,
                                                          d1, d2, option_type)

        # Calculate implied metrics
        intrinsic_value = max(0, current_price - strike_price) if option_type == "call" \
            else max(0, strike_price - current_price)
        time_value = option_price - intrinsic_value

        # Moneyness
        if option_type == "call":
            if current_price > strike_price * 1.05:
                moneyness = "In-the-money (ITM)"
            elif current_price < strike_price * 0.95:
                moneyness = "Out-of-the-money (OTM)"
            else:
                moneyness = "At-the-money (ATM)"
        else:
            if current_price < strike_price * 0.95:
                moneyness = "In-the-money (ITM)"
            elif current_price > strike_price * 1.05:
                moneyness = "Out-of-the-money (OTM)"
            else:
                moneyness = "At-the-money (ATM)"

        # Probability of profit (simplified)
        prob_itm = norm.cdf(d2) if option_type == "call" else norm.cdf(-d2)

        return {
            'underlying': {
                'ticker': ticker,
                'current_price': round(current_price, 2),
                'volatility': round(volatility * 100, 2)  # As percentage
            },
            'option_specs': {
                'type': option_type.upper(),
                'strike_price': strike_price,
                'days_to_expiry': expiry_days,
                'moneyness': moneyness
            },
            'pricing': {
                'theoretical_price': round(option_price, 2),
                'intrinsic_value': round(intrinsic_value, 2),
                'time_value': round(time_value, 2),
                'break_even': round(strike_price + option_price if option_type == "call"
                                    else strike_price - option_price, 2)
            },
            'greeks': {
                'delta': round(delta, 4),
                'gamma': round(gamma, 4),
                'theta': round(theta, 4),
                'vega': round(vega, 4),
                'rho': round(rho, 4)
            },
            'risk_metrics': {
                'probability_itm': round(prob_itm * 100, 2),
                'max_loss': round(option_price, 2),
                'max_gain': 'Unlimited' if option_type == "call" else round(strike_price - option_price, 2)
            }
        }