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

cd "$(dirname "$0")"

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Install dependencies using pip
echo "Installing dependencies with pip..."
pip install --upgrade pip
pip install -e ..

# Run the integration test script
export PYTHONPATH="$(cd .. && pwd):$PYTHONPATH"
echo "Running integration tests (test_server_integration.py)..."
python test_server_integration.py

RESULT=$?
if [ $RESULT -eq 0 ]; then
  echo "Integration tests completed successfully."
else
  echo "Integration tests failed with exit code $RESULT."
fi
