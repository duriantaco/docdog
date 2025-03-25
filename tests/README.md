# Project Owl

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/project-owl/releases)

## Overview/Introduction

Project Owl is a Python library that provides a simple and efficient way to scrape data from websites. It leverages the power of asyncio and aiohttp to perform asynchronous web requests, resulting in faster and more efficient data extraction.

The primary goal of Project Owl is to simplify the process of web scraping, allowing developers to focus on extracting and processing data instead of dealing with the complexities of handling HTTP requests and HTML parsing.

## Features

- Asynchronous web scraping using asyncio and aiohttp
- Simple and intuitive API for defining scraping tasks
- Built-in support for handling JavaScript-rendered content using Puppeteer
- Automatic handling of cookies, headers, and other request/response details
- Flexible and extensible architecture for customizing scraping logic
- Built-in caching and deduplication mechanisms
- Proxy support for scraping websites with IP restrictions

## Installation

Project Owl can be installed using pip:

```bash
pip install project-owl
```

## Quick Start Guide

Here's a basic example of how to use Project Owl to scrape data from a website:

```python
import asyncio
from project_owl import Scraper

async def main():
    scraper = Scraper()
    task = scraper.create_task('https://example.com')
    results = await task.run()
    print(results)

asyncio.run(main())
```

In this example, we create a `Scraper` instance, define a scraping task for the URL `https://example.com`, and run the task to retrieve the scraped data.

## Usage

Project Owl provides a simple and intuitive API for defining and running scraping tasks. Here's an example of how to use the library:

```python
import asyncio
from project_owl import Scraper, ScrapeTask

async def extract_data(response):
    # Custom logic for extracting data from the response
    data = response.html.find('div.data-container')
    return data

async def main():
    scraper = Scraper()
    task = ScrapeTask(
        'https://example.com',
        extract_data=extract_data,
        headers={'User-Agent': 'Mozilla/5.0'},
        use_puppeteer=True,
    )
    results = await scraper.run_task(task)
    print(results)

asyncio.run(main())
```

In this example, we define a custom `extract_data` function that will be called with the response object after the URL has been fetched. This function contains the logic for extracting the desired data from the response.

We then create a `ScrapeTask` instance, specifying the URL, the `extract_data` function, custom headers, and enabling the use of Puppeteer for JavaScript rendering.

Finally, we pass the `ScrapeTask` instance to the `Scraper.run_task` method, which performs the actual scraping and returns the extracted data.

## API Documentation

### `Scraper` Class

The `Scraper` class is the main entry point for Project Owl. It provides methods for creating and running scraping tasks.

#### Methods

- `create_task(url, **kwargs)`: Creates a new `ScrapeTask` instance with the specified URL and optional keyword arguments.
- `run_task(task)`: Runs the specified `ScrapeTask` instance and returns the extracted data.

### `ScrapeTask` Class

The `ScrapeTask` class represents a single scraping task and encapsulates the configuration and logic for extracting data from a URL.

#### Attributes

- `url`: The URL to be scraped.
- `extract_data`: A coroutine function that takes a `Response` object and returns the extracted data.
- `headers`: A dictionary of custom headers to be included in the HTTP request.
- `use_puppeteer`: A boolean flag indicating whether to use Puppeteer for JavaScript rendering.

#### Methods

- `run()`: Runs the scraping task and returns the extracted data.

## Configuration

Project Owl can be configured using environment variables or by directly modifying the configuration file (`config.py`).

### Environment Variables

- `PROXY_LIST`: A comma-separated list of proxy URLs to be used for scraping (e.g., `http://proxy1.com:8080,http://proxy2.com:8080`).
- `CACHE_DIR`: The directory path for storing cached responses (default: `~/.project_owl/cache`).
- `MAX_CACHE_SIZE`: The maximum size of the cache in bytes (default: `1024 * 1024 * 100` (100 MB)).

### Configuration File

The `config.py` file contains the following configurable options:

```python
# Proxy list
PROXY_LIST = []

# Caching
CACHE_DIR = os.path.join(os.path.expanduser('~'), '.project_owl', 'cache')
MAX_CACHE_SIZE = 1024 * 1024 * 100  # 100 MB
```

You can modify these values directly in the `config.py` file to customize the behavior of Project Owl.

## Examples and Use Cases

Here are some common use cases and examples for using Project Owl:

### Scraping a Simple Website

```python
import asyncio
from project_owl import Scraper

async def extract_data(response):
    title = response.html.find('h1', first=True).text
    paragraphs = [p.text for p in response.html.find('p')]
    return {'title': title, 'paragraphs': paragraphs}

async def main():
    scraper = Scraper()
    task = scraper.create_task('https://example.com', extract_data=extract_data)
    results = await task.run()
    print(results)

asyncio.run(main())
```

This example demonstrates how to scrape the title and paragraphs from a simple website using Project Owl.

### Scraping a JavaScript-Rendered Website

```python
import asyncio
from project_owl import Scraper, ScrapeTask

async def extract_data(response):
    products = response.html.find('div.product')
    data = []
    for product in products:
        name = product.find('h3', first=True).text
        price = product.find('span.price', first=True).text
        data.append({'name': name, 'price': price})
    return data

async def main():
    scraper = Scraper()
    task = ScrapeTask(
        'https://example.com/products',
        extract_data=extract_data,
        use_puppeteer=True,
    )
    results = await scraper.run_task(task)
    print(results)

asyncio.run(main())
```

This example demonstrates how to scrape data from a JavaScript-rendered website using Project Owl and Puppeteer. The `use_puppeteer` option is set to `True` to ensure that the website is fully rendered before extracting data.

## Troubleshooting/FAQ

### How do I handle websites with IP restrictions or rate limiting?

Project Owl supports the use of proxy servers to bypass IP restrictions and rate limiting. You can specify a list of proxy URLs in the `PROXY_LIST` environment variable or the `config.py` file. Project Owl will automatically rotate through the provided proxies for each scraping task.

### How can I control the User-Agent or other request headers?

You can specify custom headers, including the User-Agent, when creating a `ScrapeTask` instance. For example:

```python
task = ScrapeTask(
    'https://example.com',
    extract_data=extract_data,
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
)
```

### How do I handle pagination or infinite scrolling?

Project Owl provides a flexible architecture that allows you to customize the scraping logic for handling pagination or infinite scrolling. You can implement this functionality in the `extract_data` function by modifying the page state or making additional requests as needed.

## Contributing

Contributions to Project Owl are welcome! If you encounter any issues or have suggestions for improvements, please open an issue on the project's GitHub repository. If you'd like to contribute code changes, please follow these steps:

1. Fork the repository
2. Create a new branch for your feature or bug fix
3. Make your changes and commit them with descriptive commit messages
4. Push your changes to your forked repository
5. Open a pull request against the main repository

Please ensure that your code adheres to the project's coding standards and that all tests pass before submitting a pull request.

## License

Project Owl is licensed under the [Apache License 2.0](https://opensource.org/licenses/Apache-2.0).

---
*Generated by DocDog on 2025-03-25*