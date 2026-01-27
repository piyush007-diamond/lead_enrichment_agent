# Execution Directory

This directory contains **deterministic Python scripts** that perform the actual work.

## Purpose

Execution scripts handle:
- API calls to external services
- Data processing and transformation
- File operations
- Database interactions

## Guidelines

1. **Each script should be focused** - Do one thing well
2. **Use environment variables** - Load secrets from `.env`
3. **Comment thoroughly** - Document inputs, outputs, and logic
4. **Handle errors gracefully** - Return useful error messages
5. **Be testable** - Scripts should work in isolation

## Standard Script Structure

```python
#!/usr/bin/env python3
"""
Script: script_name.py
Purpose: Brief description of what this script does

Inputs:
    - arg1: Description
    - arg2: Description

Outputs:
    - Returns/saves description

Dependencies:
    - List required packages
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Main execution logic."""
    pass

if __name__ == "__main__":
    main()
```

## Environment Variables

Scripts should load API keys and secrets from the `.env` file in the project root:

```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("API_KEY_NAME")
```
