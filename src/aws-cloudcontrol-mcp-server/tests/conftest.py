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
"""Pytest configuration for AWS CloudControl API MCP Server tests."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 client."""
    return MagicMock()


@pytest.fixture
def mock_context():
    """Create a mock context."""
    context = MagicMock()
    return context
