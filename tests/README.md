# Stock Trading Analysis Tool

[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-1.0.0-blue.svg)]()

## Overview/Introduction

The Stock Trading Analysis Tool is a powerful Python-based application designed to assist traders and investors in making informed decisions through comprehensive data analysis and visualization. This tool provides a range of features to fetch historical stock data, perform technical analysis, backtest trading strategies, and generate insightful reports.

## Features

- **Data Fetching**: Retrieve historical stock data from various reliable sources (e.g., Yahoo Finance, Alpha Vantage)
- **Technical Analysis**: Perform technical analysis using popular indicators (e.g., Moving Averages, RSI, MACD)
- **Backtesting**: Backtest trading strategies on historical data to evaluate their performance
- **Visualization**: Generate interactive charts and plots for better data visualization and analysis
- **Portfolio Management**: Track and manage your investment portfolio
- **Reporting**: Generate comprehensive reports summarizing trading activities, performance, and insights

## Installation

1. Clone the repository:

```bash
git clone https://github.com/your-username/stock-trading-analysis-tool.git
```

2. Navigate to the project directory:

```bash
cd stock-trading-analysis-tool
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start Guide

To get started with the Stock Trading Analysis Tool, follow these steps:

1. Import the necessary modules:

```python
from stock_analysis import fetch_data, technical_analysis, backtesting, visualization
```

2. Fetch historical stock data:

```python
data = fetch_data.get_stock_data('AAPL', start_date='2020-01-01', end_date='2021-01-01')
```

3. Perform technical analysis:

```python
rsi = technical_analysis.calculate_rsi(data['Close'])
```

4. Backtest a trading strategy:

```python
strategy = backtesting.MovingAverageCrossStrategy(data)
results = strategy.backtest()
```

5. Visualize the results:

```python
visualization.plot_stock_data(data)
visualization.plot_indicator(data, rsi, 'RSI')
```

## Usage

The Stock Trading Analysis Tool can be used in various ways, depending on your needs. Here are some common use cases:

### Data Fetching

To fetch historical stock data, use the `fetch_data` module:

```python
from stock_analysis import fetch_data

# Fetch data from Yahoo Finance
data = fetch_data.get_stock_data_yahoo('AAPL', start_date='2020-01-01', end_date='2021-01-01')

# Fetch data from Alpha Vantage
data = fetch_data.get_stock_data_alphavantage('AAPL', start_date='2020-01-01', end_date='2021-01-01', api_key='your_api_key')
```

### Technical Analysis

The `technical_analysis` module provides functions to calculate various technical indicators:

```python
from stock_analysis import technical_analysis

# Calculate Simple Moving Average (SMA)
sma_20 = technical_analysis.calculate_sma(data['Close'], window=20)

# Calculate Relative Strength Index (RSI)
rsi = technical_analysis.calculate_rsi(data['Close'], window=14)

# Calculate Moving Average Convergence Divergence (MACD)
macd, signal = technical_analysis.calculate_macd(data['Close'], fast=12, slow=26, signal=9)
```

### Backtesting

The `backtesting` module allows you to backtest trading strategies on historical data:

```python
from stock_analysis import backtesting

# Create a simple Moving Average Crossover strategy
strategy = backtesting.MovingAverageCrossStrategy(data, short_window=20, long_window=50)

# Backtest the strategy
results = strategy.backtest()

# Print the performance metrics
print(results.metrics)
```

### Visualization

The `visualization` module provides functions to create interactive charts and plots:

```python
from stock_analysis import visualization

# Plot stock data
visualization.plot_stock_data(data)

# Plot technical indicators
visualization.plot_indicator(data, sma_20, 'SMA (20)')
visualization.plot_indicator(data, rsi, 'RSI')

# Plot trading signals
visualization.plot_trading_signals(data, results.signals)
```

### Portfolio Management

The `portfolio` module helps you manage your investment portfolio:

```python
from stock_analysis import portfolio

# Create a new portfolio
my_portfolio = portfolio.Portfolio()

# Add stocks to the portfolio
my_portfolio.add_stock('AAPL', 100, 120.50)
my_portfolio.add_stock('GOOG', 50, 2500.75)

# Calculate the portfolio value
portfolio_value = my_portfolio.calculate_value()
print(f'Portfolio Value: ${portfolio_value:.2f}')
```

### Reporting

The `reporting` module generates comprehensive reports summarizing trading activities, performance, and insights:

```python
from stock_analysis import reporting

# Generate a performance report
report = reporting.generate_performance_report(results)
report.to_pdf('performance_report.pdf')

# Generate a trading summary report
summary = reporting.generate_trading_summary(data, results.signals)
summary.to_excel('trading_summary.xlsx')
```

## API Documentation

The Stock Trading Analysis Tool provides the following main classes and functions:

### `fetch_data` module

- `get_stock_data_yahoo(ticker, start_date, end_date)`: Fetches historical stock data from Yahoo Finance.
- `get_stock_data_alphavantage(ticker, start_date, end_date, api_key)`: Fetches historical stock data from Alpha Vantage.

### `technical_analysis` module

- `calculate_sma(data, window)`: Calculates the Simple Moving Average (SMA) indicator.
- `calculate_rsi(data, window)`: Calculates the Relative Strength Index (RSI) indicator.
- `calculate_macd(data, fast, slow, signal)`: Calculates the Moving Average Convergence Divergence (MACD) indicator.

### `backtesting` module

- `MovingAverageCrossStrategy(data, short_window, long_window)`: A class representing a simple Moving Average Crossover trading strategy.
  - `backtest()`: Backtests the strategy on the provided data and returns the results.

### `visualization` module

- `plot_stock_data(data)`: Plots the stock data (Open, High, Low, Close) over time.
- `plot_indicator(data, indicator, label)`: Plots a technical indicator overlaid on the stock data.
- `plot_trading_signals(data, signals)`: Plots the trading signals (buy/sell) on the stock data.

### `portfolio` module

- `Portfolio()`: A class representing an investment portfolio.
  - `add_stock(ticker, shares, price)`: Adds a stock to the portfolio.
  - `calculate_value()`: Calculates the current value of the portfolio.

### `reporting` module

- `generate_performance_report(results)`: Generates a report summarizing the performance of a backtested strategy.
- `generate_trading_summary(data, signals)`: Generates a report summarizing the trading activities and signals.

## Configuration

The Stock Trading Analysis Tool can be configured using environment variables or a configuration file (e.g., `config.py`). Here are some common configuration options:

- `DATA_SOURCE`: The source for fetching historical stock data (e.g., 'yahoo', 'alphavantage').
- `ALPHAVANTAGE_API_KEY`: The API key for Alpha Vantage, if using that data source.
- `TRADING_CAPITAL`: The initial capital for backtesting trading strategies.
- `RISK_PERCENTAGE`: The maximum risk percentage for each trade.

## Examples and Use Cases

Here are some examples and common use cases for the Stock Trading Analysis Tool:

### Simple Moving Average Crossover Strategy

```python
from stock_analysis import fetch_data, technical_analysis, backtesting, visualization

# Fetch data
data = fetch_data.get_stock_data_yahoo('AAPL', start_date='2020-01-01', end_date='2021-01-01')

# Calculate moving averages
sma_20 = technical_analysis.calculate_sma(data['Close'], window=20)
sma_50 = technical_analysis.calculate_sma(data['Close'], window=50)

# Create and backtest the strategy
strategy = backtesting.MovingAverageCrossStrategy(data, short_window=20, long_window=50)
results = strategy.backtest()

# Plot the results
visualization.plot_stock_data(data)
visualization.plot_indicator(data, sma_20, 'SMA (20)')
visualization.plot_indicator(data, sma_50, 'SMA (50)')
visualization.plot_trading_signals(data, results.signals)
```

### RSI-based Trading Strategy

```python
from stock_analysis import fetch_data, technical_analysis, backtesting, visualization

# Fetch data
data = fetch_data.get_stock_data_yahoo('GOOG', start_date='2021-01-01', end_date='2021-12-31')

# Calculate RSI
rsi = technical_analysis.calculate_rsi(data['Close'], window=14)

# Create and backtest the strategy
strategy = backtesting.RSIStrategy(data, rsi_window=14, overbought=70, oversold=30)
results = strategy.backtest()

# Plot the results
visualization.plot_stock_data(data)
visualization.plot_indicator(data, rsi, 'RSI')
visualization.plot_trading_signals(data, results.signals)
```

### Portfolio Management

```python
from stock_analysis import portfolio

# Create a new portfolio
my_portfolio = portfolio.Portfolio()

# Add stocks to the portfolio
my_portfolio.add_stock('AAPL', 100, 120.50)
my_portfolio.add_stock('GOOG', 50, 2500.75)
my_portfolio.add_stock('AMZN', 25, 3200.00)

# Calculate the portfolio value
portfolio_value = my_portfolio.calculate_value()
print(f'Portfolio Value: ${portfolio_value:.2f}')

# Generate a portfolio report
report = my_portfolio.generate_report()
report.to_excel('portfolio_report.xlsx')
```

## Troubleshooting/FAQ

1. **Error fetching data from Alpha Vantage**:
   - Check if your API key is valid and has the required permissions.
   - Ensure that you're using the correct API endpoint and parameters.

2. **Backtesting results show unexpected behavior**:
   - Verify that your trading strategy logic is correct and matches your expectations.
   - Check if there are any data quality issues or missing values in the historical data.

3. **Visualization plots are not rendering correctly**:
   - Make sure you have installed all the required dependencies for visualization (e.g., Matplotlib, Plotly).
   - Check if your data is in the correct format and doesn't contain any missing or invalid values.

4. **Portfolio management errors**:
   - Ensure that you're providing the correct stock tickers, shares, and prices when adding stocks to the portfolio.
   - Verify that the stock data is up-to-date and doesn't contain any errors or missing values.

## Contributing

Contributions to the Stock Trading Analysis Tool are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request on the project's GitHub repository.

When contributing, please follow these guidelines:

1. Fork the repository and create a new branch for your feature or bug fix.
2. Make your changes and ensure that the code follows the project's coding style and conventions.
3. Add tests for your changes, if applicable.
4. Update the documentation with any relevant changes.
5. Submit a pull request with a detailed description of your changes.

## License

This project is licensed under the [MIT License](LICENSE).

---
*Generated by DocDog on 2025-03-25*