# Contributing to DocDog

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report for DocDog. Following these guidelines helps maintainers understand your report.

**How Do I Submit A Bug Report?**
* Report the bug in the repo page by opening an issue
* Use a clear and descriptive title
* Describe the exact steps to reproduce the problem
* Describe the behavior you observed and why it is a problem
* Include any relevant log outputs
* Specify your Python version, and DocDog version

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for DocDog.

**How Do I Submit An Enhancement Suggestion?**
* Send your suggestions in the repo page by opening an issue
* Use a clear and descriptive title
* Provide a detailed description of the proposed functionality

### Pull Requests

* Fill in the required template
* Follow the Python style guide (we use PEP 8)
* Include tests for new functionality
* Update documentation when changing functionality

## Development Process

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/duriantaco/docdog.git
cd docdog

# Create a virtual environment with uv
uv venv venv
source venv/bin/activate  

# Install the package in development mode
uv pip install -e .

# Install development dependencies
uv pip install pytest pytest-cov
```

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=docdog
```

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms.

## Questions?

Feel free to reach out if you have any questions about contributing! Thanks! :) 