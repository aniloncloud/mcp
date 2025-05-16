#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

set -e

# Create and activate virtual environment
VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install boto3 botocore loguru pydantic pytest pytest-asyncio pytest-cov

# Install the package in development mode
echo "Installing package in development mode..."
pip install -e .

# Run tests with coverage
echo "Running tests with coverage..."
python -m pytest tests/ -v --cov=awslabs.aws_cloudcontrol_server --cov-report=term --cov-report=xml
