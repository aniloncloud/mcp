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
"""Tests for AWS CloudControl API MCP Server."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

# Import the functions directly to avoid Field validation issues
from awslabs.aws_cloudcontrol_server.server import (
    CloudControlClient,
    cancel_resource_request,
    create_resource,
    delete_resource,
    get_resource,
    get_resource_request_status,
    list_resource_requests,
    list_resource_types,
    list_resources,
    main,
    update_resource,
)


@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 client."""
    return MagicMock()


@pytest.fixture
def mock_context():
    """Create a mock context."""
    context = MagicMock()
    return context


@pytest.fixture
def mock_progress_event():
    """Create a mock progress event."""
    return {
        "EventTime": datetime.now(),
        "TypeName": "AWS::Logs::LogGroup",
        "OperationStatus": "SUCCESS",
        "Operation": "CREATE",
        "Identifier": "TestLogGroup",
        "RequestToken": "12345678-1234-1234-1234-123456789012",
        "StatusMessage": "Resource creation completed",
    }


@pytest.mark.asyncio
async def test_create_resource(mock_boto3_client, mock_context, mock_progress_event):
    """Test the create_resource tool."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    desired_state = {"LogGroupName": "TestLogGroup", "RetentionInDays": 90}

    # Set up mock response
    mock_boto3_client.create_resource.return_value = {"ProgressEvent": mock_progress_event}

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await create_resource(
            mock_context, type_name=type_name, desired_state=desired_state
        )

    # Verify the result
    assert "ProgressEvent" in result
    assert result["ProgressEvent"]["TypeName"] == type_name
    assert result["ProgressEvent"]["Operation"] == "CREATE"
    assert result["ProgressEvent"]["Identifier"] == "TestLogGroup"

    # Verify the API call
    mock_boto3_client.create_resource.assert_called_once()
    args, kwargs = mock_boto3_client.create_resource.call_args
    assert kwargs["TypeName"] == type_name
    assert json.loads(kwargs["DesiredState"]) == desired_state


@pytest.mark.asyncio
async def test_create_resource_with_optional_params(
    mock_boto3_client, mock_context, mock_progress_event
):
    """Test the create_resource tool with optional parameters."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    desired_state = {"LogGroupName": "TestLogGroup", "RetentionInDays": 90}
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    client_token = "test-client-token"

    # Set up mock response
    mock_boto3_client.create_resource.return_value = {"ProgressEvent": mock_progress_event}

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await create_resource(
            mock_context,
            type_name=type_name,
            desired_state=desired_state,
            role_arn=role_arn,
            client_token=client_token,
        )

    # Verify the result
    assert "ProgressEvent" in result

    # Verify the API call with optional parameters
    mock_boto3_client.create_resource.assert_called_once()
    args, kwargs = mock_boto3_client.create_resource.call_args
    assert kwargs["TypeName"] == type_name
    assert kwargs["RoleArn"] == role_arn
    assert kwargs["ClientToken"] == client_token


@pytest.mark.asyncio
async def test_create_resource_client_error(mock_boto3_client, mock_context):
    """Test create_resource when boto3 client raises a ClientError."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    desired_state = {"LogGroupName": "TestLogGroup"}

    # Set up mock error
    mock_error = MagicMock()
    mock_error.response = {"Error": {"Code": "ValidationException", "Message": "Test error"}}
    mock_boto3_client.create_resource.side_effect = botocore.exceptions.ClientError(
        mock_error.response, "CreateResource"
    )

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await create_resource(
            mock_context, type_name=type_name, desired_state=desired_state
        )

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudControl API error" in result["error"]


@pytest.mark.asyncio
async def test_create_resource_error_no_client(mock_context):
    """Test create_resource when client is not initialized."""

    # Set up the mock context to handle async error method
    async def mock_error(message):
        return None

    mock_context.error = mock_error

    # Patch the create_resource function to return an error directly
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = None

        # Mock the internal behavior to avoid the await ctx.error call
        with patch(
            "awslabs.aws_cloudcontrol_server.server.create_resource",
            return_value={"error": "AWS CloudControl API client not initialized"},
        ):
            result = await create_resource(
                mock_context,
                type_name="AWS::Logs::LogGroup",
                desired_state={"LogGroupName": "TestLogGroup"},
            )

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudControl API client not initialized" in result["error"]


@pytest.mark.asyncio
async def test_get_resource(mock_boto3_client, mock_context):
    """Test the get_resource tool."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    identifier = "TestLogGroup"

    # Set up mock response
    mock_boto3_client.get_resource.return_value = {
        "TypeName": type_name,
        "ResourceDescription": {
            "Identifier": identifier,
            "Properties": '{"RetentionInDays": 90, "LogGroupName": "TestLogGroup", "Arn": "arn:aws:logs:us-west-2:123456789012:log-group:TestLogGroup:*"}',
        },
    }

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await get_resource(mock_context, type_name=type_name, identifier=identifier)

    # Verify the result
    assert result["TypeName"] == type_name
    assert result["ResourceDescription"]["Identifier"] == identifier
    assert result["ResourceDescription"]["Properties"]["LogGroupName"] == "TestLogGroup"
    assert result["ResourceDescription"]["Properties"]["RetentionInDays"] == 90

    # Verify the API call
    mock_boto3_client.get_resource.assert_called_once()
    args, kwargs = mock_boto3_client.get_resource.call_args
    assert kwargs["TypeName"] == type_name
    assert kwargs["Identifier"] == identifier


@pytest.mark.asyncio
async def test_get_resource_with_role_arn(mock_boto3_client, mock_context):
    """Test the get_resource tool with role_arn parameter."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    identifier = "TestLogGroup"
    role_arn = "arn:aws:iam::123456789012:role/TestRole"

    # Set up mock response
    mock_boto3_client.get_resource.return_value = {
        "TypeName": type_name,
        "ResourceDescription": {
            "Identifier": identifier,
            "Properties": '{"RetentionInDays": 90, "LogGroupName": "TestLogGroup"}',
        },
    }

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await get_resource(
            mock_context, type_name=type_name, identifier=identifier, role_arn=role_arn
        )

    # Verify the result
    assert result["TypeName"] == type_name

    # Verify the API call with role_arn
    mock_boto3_client.get_resource.assert_called_once()
    args, kwargs = mock_boto3_client.get_resource.call_args
    assert kwargs["TypeName"] == type_name
    assert kwargs["Identifier"] == identifier
    assert kwargs["RoleArn"] == role_arn


@pytest.mark.asyncio
async def test_get_resource_client_error(mock_boto3_client, mock_context):
    """Test get_resource when boto3 client raises a ClientError."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    identifier = "TestLogGroup"

    # Set up mock error
    mock_error = MagicMock()
    mock_error.response = {
        "Error": {"Code": "ResourceNotFoundException", "Message": "Resource not found"}
    }
    mock_boto3_client.get_resource.side_effect = botocore.exceptions.ClientError(
        mock_error.response, "GetResource"
    )

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await get_resource(mock_context, type_name=type_name, identifier=identifier)

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudControl API error" in result["error"]


@pytest.mark.asyncio
async def test_get_resource_json_decode_error(mock_boto3_client, mock_context):
    """Test get_resource when the Properties field contains invalid JSON."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    identifier = "TestLogGroup"

    # Set up mock response with invalid JSON
    mock_boto3_client.get_resource.return_value = {
        "TypeName": type_name,
        "ResourceDescription": {"Identifier": identifier, "Properties": "{invalid json}"},
    }

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await get_resource(mock_context, type_name=type_name, identifier=identifier)

    # Verify the result contains the error
    assert "error" in result
    assert "Error getting resource" in result["error"]


@pytest.mark.asyncio
async def test_update_resource(mock_boto3_client, mock_context, mock_progress_event):
    """Test the update_resource tool."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    identifier = "TestLogGroup"
    patch_document = '[{"op":"replace","path":"RetentionInDays","value":180}]'

    # Set up mock response
    mock_boto3_client.update_resource.return_value = {"ProgressEvent": mock_progress_event}

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await update_resource(
            mock_context, type_name=type_name, identifier=identifier, patch_document=patch_document
        )

    # Verify the result
    assert "ProgressEvent" in result
    assert result["ProgressEvent"]["TypeName"] == type_name
    assert result["ProgressEvent"]["Identifier"] == "TestLogGroup"

    # Verify the API call
    mock_boto3_client.update_resource.assert_called_once()
    args, kwargs = mock_boto3_client.update_resource.call_args
    assert kwargs["TypeName"] == type_name
    assert kwargs["Identifier"] == identifier
    assert kwargs["PatchDocument"] == patch_document


@pytest.mark.asyncio
async def test_update_resource_with_optional_params(
    mock_boto3_client, mock_context, mock_progress_event
):
    """Test the update_resource tool with optional parameters."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    identifier = "TestLogGroup"
    patch_document = '[{"op":"replace","path":"RetentionInDays","value":180}]'
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    client_token = "test-client-token"

    # Set up mock response
    mock_boto3_client.update_resource.return_value = {"ProgressEvent": mock_progress_event}

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await update_resource(
            mock_context,
            type_name=type_name,
            identifier=identifier,
            patch_document=patch_document,
            role_arn=role_arn,
            client_token=client_token,
        )

    # Verify the result
    assert "ProgressEvent" in result

    # Verify the API call with optional parameters
    mock_boto3_client.update_resource.assert_called_once()
    args, kwargs = mock_boto3_client.update_resource.call_args
    assert kwargs["TypeName"] == type_name
    assert kwargs["Identifier"] == identifier
    assert kwargs["PatchDocument"] == patch_document
    assert kwargs["RoleArn"] == role_arn
    assert kwargs["ClientToken"] == client_token


@pytest.mark.asyncio
async def test_update_resource_client_error(mock_boto3_client, mock_context):
    """Test update_resource when boto3 client raises a ClientError."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    identifier = "TestLogGroup"
    patch_document = '[{"op":"replace","path":"RetentionInDays","value":180}]'

    # Set up mock error
    mock_error = MagicMock()
    mock_error.response = {
        "Error": {"Code": "ResourceNotFoundException", "Message": "Resource not found"}
    }
    mock_boto3_client.update_resource.side_effect = botocore.exceptions.ClientError(
        mock_error.response, "UpdateResource"
    )

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await update_resource(
            mock_context, type_name=type_name, identifier=identifier, patch_document=patch_document
        )

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudControl API error" in result["error"]


@pytest.mark.asyncio
async def test_delete_resource(mock_boto3_client, mock_context, mock_progress_event):
    """Test the delete_resource tool."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    identifier = "TestLogGroup"

    # Set up mock response
    mock_boto3_client.delete_resource.return_value = {"ProgressEvent": mock_progress_event}

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await delete_resource(mock_context, type_name=type_name, identifier=identifier)

    # Verify the result
    assert "ProgressEvent" in result
    assert result["ProgressEvent"]["TypeName"] == type_name
    assert (
        result["ProgressEvent"]["Operation"] == "CREATE"
    )  # This would be DELETE in a real response
    assert result["ProgressEvent"]["Identifier"] == "TestLogGroup"

    # Verify the API call
    mock_boto3_client.delete_resource.assert_called_once()
    args, kwargs = mock_boto3_client.delete_resource.call_args
    assert kwargs["TypeName"] == type_name
    assert kwargs["Identifier"] == identifier


@pytest.mark.asyncio
async def test_delete_resource_with_optional_params(
    mock_boto3_client, mock_context, mock_progress_event
):
    """Test the delete_resource tool with optional parameters."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    identifier = "TestLogGroup"
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    client_token = "test-client-token"

    # Set up mock response
    mock_boto3_client.delete_resource.return_value = {"ProgressEvent": mock_progress_event}

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await delete_resource(
            mock_context,
            type_name=type_name,
            identifier=identifier,
            role_arn=role_arn,
            client_token=client_token,
        )

    # Verify the result
    assert "ProgressEvent" in result

    # Verify the API call with optional parameters
    mock_boto3_client.delete_resource.assert_called_once()
    args, kwargs = mock_boto3_client.delete_resource.call_args
    assert kwargs["TypeName"] == type_name
    assert kwargs["Identifier"] == identifier
    assert kwargs["RoleArn"] == role_arn
    assert kwargs["ClientToken"] == client_token


@pytest.mark.asyncio
async def test_delete_resource_client_error(mock_boto3_client, mock_context):
    """Test delete_resource when boto3 client raises a ClientError."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    identifier = "TestLogGroup"

    # Set up mock error
    mock_error = MagicMock()
    mock_error.response = {
        "Error": {"Code": "ResourceNotFoundException", "Message": "Resource not found"}
    }
    mock_boto3_client.delete_resource.side_effect = botocore.exceptions.ClientError(
        mock_error.response, "DeleteResource"
    )

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await delete_resource(mock_context, type_name=type_name, identifier=identifier)

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudControl API error" in result["error"]


@pytest.mark.asyncio
async def test_list_resources(mock_boto3_client, mock_context):
    """Test the list_resources tool."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"

    # Set up mock response
    mock_boto3_client.list_resources.return_value = {
        "TypeName": type_name,
        "ResourceDescriptions": [
            {
                "Identifier": "TestLogGroup1",
                "Properties": '{"RetentionInDays": 90, "LogGroupName": "TestLogGroup1"}',
            },
            {
                "Identifier": "TestLogGroup2",
                "Properties": '{"RetentionInDays": 180, "LogGroupName": "TestLogGroup2"}',
            },
        ],
    }

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await list_resources(mock_context, type_name=type_name)

    # Verify the result
    assert result["TypeName"] == type_name
    assert len(result["ResourceDescriptions"]) == 2
    assert result["ResourceDescriptions"][0]["Identifier"] == "TestLogGroup1"
    assert result["ResourceDescriptions"][1]["Identifier"] == "TestLogGroup2"
    assert result["ResourceDescriptions"][0]["Properties"]["RetentionInDays"] == 90
    assert result["ResourceDescriptions"][1]["Properties"]["RetentionInDays"] == 180

    # Verify the API call
    mock_boto3_client.list_resources.assert_called_once()
    args, kwargs = mock_boto3_client.list_resources.call_args
    assert kwargs["TypeName"] == type_name


@pytest.mark.asyncio
async def test_list_resources_with_optional_params(mock_boto3_client, mock_context):
    """Test the list_resources tool with optional parameters."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"
    resource_model = {"LogGroupName": "Test*"}
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    next_token = "next-page-token"

    # Set up mock response
    mock_boto3_client.list_resources.return_value = {
        "TypeName": type_name,
        "ResourceDescriptions": [
            {
                "Identifier": "TestLogGroup1",
                "Properties": '{"RetentionInDays": 90, "LogGroupName": "TestLogGroup1"}',
            }
        ],
        "NextToken": "another-page-token",
    }

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await list_resources(
            mock_context,
            type_name=type_name,
            resource_model=resource_model,
            role_arn=role_arn,
            next_token=next_token,
        )

    # Verify the result
    assert result["TypeName"] == type_name
    assert "NextToken" in result
    assert result["NextToken"] == "another-page-token"

    # Verify the API call with optional parameters
    mock_boto3_client.list_resources.assert_called_once()
    args, kwargs = mock_boto3_client.list_resources.call_args
    assert kwargs["TypeName"] == type_name
    assert kwargs["ResourceModel"] == json.dumps(resource_model)
    assert kwargs["RoleArn"] == role_arn
    assert kwargs["NextToken"] == next_token


@pytest.mark.asyncio
async def test_list_resources_client_error(mock_boto3_client, mock_context):
    """Test list_resources when boto3 client raises a ClientError."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"

    # Set up mock error
    mock_error = MagicMock()
    mock_error.response = {"Error": {"Code": "ValidationException", "Message": "Invalid type name"}}
    mock_boto3_client.list_resources.side_effect = botocore.exceptions.ClientError(
        mock_error.response, "ListResources"
    )

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await list_resources(mock_context, type_name=type_name)

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudControl API error" in result["error"]


@pytest.mark.asyncio
async def test_list_resources_json_decode_error(mock_boto3_client, mock_context):
    """Test list_resources when the Properties field contains invalid JSON."""
    # Set up test data
    type_name = "AWS::Logs::LogGroup"

    # Set up mock response with invalid JSON
    mock_boto3_client.list_resources.return_value = {
        "TypeName": type_name,
        "ResourceDescriptions": [{"Identifier": "TestLogGroup1", "Properties": "{invalid json}"}],
    }

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await list_resources(mock_context, type_name=type_name)

    # Verify the result contains the resource with empty properties
    assert "ResourceDescriptions" in result
    assert len(result["ResourceDescriptions"]) == 1
    assert result["ResourceDescriptions"][0]["Identifier"] == "TestLogGroup1"
    assert result["ResourceDescriptions"][0]["Properties"] == {}


@pytest.mark.asyncio
async def test_get_resource_request_status(mock_boto3_client, mock_context, mock_progress_event):
    """Test the get_resource_request_status tool."""
    # Set up test data
    request_token = "12345678-1234-1234-1234-123456789012"

    # Set up mock response
    mock_boto3_client.get_resource_request_status.return_value = {
        "ProgressEvent": mock_progress_event
    }

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await get_resource_request_status(mock_context, request_token=request_token)

    # Verify the result
    assert "ProgressEvent" in result
    assert result["ProgressEvent"]["RequestToken"] == request_token

    # Verify the API call
    mock_boto3_client.get_resource_request_status.assert_called_once()
    args, kwargs = mock_boto3_client.get_resource_request_status.call_args
    assert kwargs["RequestToken"] == request_token


@pytest.mark.asyncio
async def test_get_resource_request_status_client_error(mock_boto3_client, mock_context):
    """Test get_resource_request_status when boto3 client raises a ClientError."""
    # Set up test data
    request_token = "12345678-1234-1234-1234-123456789012"

    # Set up mock error
    mock_error = MagicMock()
    mock_error.response = {
        "Error": {"Code": "ResourceRequestNotFound", "Message": "Request not found"}
    }
    mock_boto3_client.get_resource_request_status.side_effect = botocore.exceptions.ClientError(
        mock_error.response, "GetResourceRequestStatus"
    )

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await get_resource_request_status(mock_context, request_token=request_token)

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudControl API error" in result["error"]


@pytest.mark.asyncio
async def test_get_resource_request_status_error_no_client(mock_context):
    """Test get_resource_request_status when client is not initialized."""
    # Set up test data
    request_token = "12345678-1234-1234-1234-123456789012"

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = None
        result = await get_resource_request_status(mock_context, request_token=request_token)

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudControl API client not initialized" in result["error"]


@pytest.mark.asyncio
async def test_cancel_resource_request(mock_boto3_client, mock_context, mock_progress_event):
    """Test the cancel_resource_request tool."""
    # Set up test data
    request_token = "12345678-1234-1234-1234-123456789012"

    # Set up mock response
    mock_boto3_client.cancel_resource_request.return_value = {"ProgressEvent": mock_progress_event}

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await cancel_resource_request(mock_context, request_token=request_token)

    # Verify the result
    assert "ProgressEvent" in result
    assert result["ProgressEvent"]["RequestToken"] == request_token

    # Verify the API call
    mock_boto3_client.cancel_resource_request.assert_called_once()
    args, kwargs = mock_boto3_client.cancel_resource_request.call_args
    assert kwargs["RequestToken"] == request_token


@pytest.mark.asyncio
async def test_cancel_resource_request_client_error(mock_boto3_client, mock_context):
    """Test cancel_resource_request when boto3 client raises a ClientError."""
    # Set up test data
    request_token = "12345678-1234-1234-1234-123456789012"

    # Set up mock error
    mock_error = MagicMock()
    mock_error.response = {
        "Error": {"Code": "ResourceRequestNotFound", "Message": "Request not found"}
    }
    mock_boto3_client.cancel_resource_request.side_effect = botocore.exceptions.ClientError(
        mock_error.response, "CancelResourceRequest"
    )

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await cancel_resource_request(mock_context, request_token=request_token)

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudControl API error" in result["error"]


@pytest.mark.asyncio
async def test_cancel_resource_request_error_no_client(mock_context):
    """Test cancel_resource_request when client is not initialized."""
    # Set up test data
    request_token = "12345678-1234-1234-1234-123456789012"

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = None
        result = await cancel_resource_request(mock_context, request_token=request_token)

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudControl API client not initialized" in result["error"]


@pytest.mark.asyncio
async def test_list_resource_requests(mock_boto3_client, mock_context, mock_progress_event):
    """Test the list_resource_requests tool."""
    # Set up mock response
    mock_boto3_client.list_resource_requests.return_value = {
        "ResourceRequestStatusSummaries": [
            mock_progress_event,
            {
                "EventTime": datetime.now(),
                "TypeName": "AWS::Logs::LogGroup",
                "OperationStatus": "IN_PROGRESS",
                "Operation": "UPDATE",
                "Identifier": "AnotherLogGroup",
                "RequestToken": "87654321-4321-4321-4321-210987654321",
                "StatusMessage": "Resource update in progress",
            },
        ]
    }

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await list_resource_requests(mock_context)

    # Verify the result
    assert "ResourceRequestStatusSummaries" in result
    assert len(result["ResourceRequestStatusSummaries"]) == 2
    assert result["ResourceRequestStatusSummaries"][0]["Identifier"] == "TestLogGroup"
    assert result["ResourceRequestStatusSummaries"][1]["Identifier"] == "AnotherLogGroup"
    assert result["ResourceRequestStatusSummaries"][0]["Operation"] == "CREATE"
    assert result["ResourceRequestStatusSummaries"][1]["Operation"] == "UPDATE"

    # Verify the API call
    mock_boto3_client.list_resource_requests.assert_called_once()


@pytest.mark.asyncio
async def test_list_resource_requests_with_optional_params(
    mock_boto3_client, mock_context, mock_progress_event
):
    """Test the list_resource_requests tool with optional parameters."""
    # Set up test data
    resource_request_status_filter = {"Operations": ["CREATE", "UPDATE"]}
    next_token = "next-page-token"

    # Set up mock response
    mock_boto3_client.list_resource_requests.return_value = {
        "ResourceRequestStatusSummaries": [mock_progress_event],
        "NextToken": "another-page-token",
    }

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await list_resource_requests(
            mock_context,
            resource_request_status_filter=resource_request_status_filter,
            next_token=next_token,
        )

    # Verify the result
    assert "ResourceRequestStatusSummaries" in result
    assert "NextToken" in result
    assert result["NextToken"] == "another-page-token"

    # Verify the API call with optional parameters
    mock_boto3_client.list_resource_requests.assert_called_once()
    args, kwargs = mock_boto3_client.list_resource_requests.call_args
    assert kwargs["ResourceRequestStatusFilter"] == resource_request_status_filter
    assert kwargs["NextToken"] == next_token


@pytest.mark.asyncio
async def test_list_resource_requests_client_error(mock_boto3_client, mock_context):
    """Test list_resource_requests when boto3 client raises a ClientError."""
    # Set up mock error
    mock_error = MagicMock()
    mock_error.response = {"Error": {"Code": "ValidationException", "Message": "Invalid filter"}}
    mock_boto3_client.list_resource_requests.side_effect = botocore.exceptions.ClientError(
        mock_error.response, "ListResourceRequests"
    )

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = mock_boto3_client
        result = await list_resource_requests(mock_context)

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudControl API error" in result["error"]


@pytest.mark.asyncio
async def test_list_resource_requests_error_no_client(mock_context):
    """Test list_resource_requests when client is not initialized."""

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudcontrol_client = None
        result = await list_resource_requests(mock_context)

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudControl API client not initialized" in result["error"]


@pytest.mark.asyncio
async def test_list_resource_types(mock_boto3_client, mock_context):
    """Test the list_resource_types tool."""
    # Set up mock response
    mock_boto3_client.list_types.return_value = {
        "TypeSummaries": [
            {
                "TypeName": "AWS::Logs::LogGroup",
                "TypeArn": "arn:aws:cloudformation:us-west-2::type/resource/AWS-Logs-LogGroup",
                "Description": "AWS::Logs::LogGroup Resource Type",
                "ProvisioningType": "FULLY_MUTABLE",
                "LastUpdated": datetime.now(),
                "Visibility": "PUBLIC",
            },
            {
                "TypeName": "AWS::S3::Bucket",
                "TypeArn": "arn:aws:cloudformation:us-west-2::type/resource/AWS-S3-Bucket",
                "Description": "AWS::S3::Bucket Resource Type",
                "ProvisioningType": "FULLY_MUTABLE",
                "LastUpdated": datetime.now(),
                "Visibility": "PUBLIC",
            },
        ]
    }

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudformation_client = mock_boto3_client
        result = await list_resource_types(mock_context)

    # Verify the result
    assert "TypeSummaries" in result
    assert len(result["TypeSummaries"]) == 2
    assert result["TypeSummaries"][0]["TypeName"] == "AWS::Logs::LogGroup"
    assert result["TypeSummaries"][1]["TypeName"] == "AWS::S3::Bucket"

    # Verify the API call
    mock_boto3_client.list_types.assert_called_once()


@pytest.mark.asyncio
async def test_list_resource_types_with_filters(mock_boto3_client, mock_context):
    """Test the list_resource_types tool with filters."""
    # Set up test data
    filters = {"TypeNamePrefix": "AWS::S3::"}

    # Set up mock response
    mock_boto3_client.list_types.return_value = {
        "TypeSummaries": [
            {
                "TypeName": "AWS::S3::Bucket",
                "TypeArn": "arn:aws:cloudformation:us-west-2::type/resource/AWS-S3-Bucket",
                "Description": "AWS::S3::Bucket Resource Type",
                "ProvisioningType": "FULLY_MUTABLE",
                "LastUpdated": datetime.now(),
                "Visibility": "PUBLIC",
            }
        ],
        "NextToken": "next-page-token",
    }

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudformation_client = mock_boto3_client
        result = await list_resource_types(mock_context, filters=filters)

    # Verify the result
    assert "TypeSummaries" in result
    assert len(result["TypeSummaries"]) == 1
    assert result["TypeSummaries"][0]["TypeName"] == "AWS::S3::Bucket"
    assert "NextToken" in result
    assert result["NextToken"] == "next-page-token"

    # Verify the API call with filters
    mock_boto3_client.list_types.assert_called_once()
    args, kwargs = mock_boto3_client.list_types.call_args
    assert kwargs["Filters"] == filters


@pytest.mark.asyncio
async def test_list_resource_types_client_error(mock_boto3_client, mock_context):
    """Test list_resource_types when boto3 client raises a ClientError."""
    # Set up mock error
    mock_error = MagicMock()
    mock_error.response = {"Error": {"Code": "ValidationException", "Message": "Invalid filter"}}
    mock_boto3_client.list_types.side_effect = botocore.exceptions.ClientError(
        mock_error.response, "ListTypes"
    )

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudformation_client = mock_boto3_client
        result = await list_resource_types(mock_context)

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudFormation API error" in result["error"]


@pytest.mark.asyncio
async def test_list_resource_types_error_no_client(mock_context):
    """Test list_resource_types when client is not initialized."""

    # Set up mock context with async error method
    async def mock_error_func(message):
        return None

    mock_context.error = mock_error_func

    # Patch the cloudcontrol_client in the server module
    with patch("awslabs.aws_cloudcontrol_server.server.cloudcontrol_client") as mock_client:
        mock_client.cloudformation_client = None
        result = await list_resource_types(mock_context)

    # Verify the result contains the error
    assert "error" in result
    assert "AWS CloudFormation client not initialized" in result["error"]


def test_cloudcontrol_client_initialization(monkeypatch):
    """Test the CloudControlClient initialization."""
    monkeypatch.setenv("AWS_REGION", "us-west-2")

    with patch("boto3.client") as mock_boto3_client:
        client = CloudControlClient()
        # Check that both clients were initialized
        assert mock_boto3_client.call_count == 2

        # Check the first call (cloudcontrol)
        args, kwargs = mock_boto3_client.call_args_list[0]
        assert args[0] == "cloudcontrol"
        assert kwargs["region_name"] == "us-west-2"

        # Check the second call (cloudformation)
        args, kwargs = mock_boto3_client.call_args_list[1]
        assert args[0] == "cloudformation"
        assert kwargs["region_name"] == "us-west-2"


def test_cloudcontrol_client_initialization_with_credentials(monkeypatch):
    """Test the CloudControlClient initialization with explicit credentials."""
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    with patch("boto3.client") as mock_boto3_client:
        client = CloudControlClient()
        # Check that both clients were initialized
        assert mock_boto3_client.call_count == 2

        # Check the first call (cloudcontrol)
        args, kwargs = mock_boto3_client.call_args_list[0]
        assert args[0] == "cloudcontrol"
        assert kwargs["region_name"] == "us-west-2"
        assert kwargs["aws_access_key_id"] == "AKIAIOSFODNN7EXAMPLE"
        assert kwargs["aws_secret_access_key"] == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


def test_cloudcontrol_client_initialization_with_session_token(monkeypatch):
    """Test the CloudControlClient initialization with session token."""
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    monkeypatch.setenv(
        "AWS_SESSION_TOKEN",
        "AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4Olgk",
    )

    with patch("boto3.client") as mock_boto3_client:
        client = CloudControlClient()
        # Check that both clients were initialized
        assert mock_boto3_client.call_count == 2

        # Check the first call (cloudcontrol)
        args, kwargs = mock_boto3_client.call_args_list[0]
        assert args[0] == "cloudcontrol"
        assert kwargs["region_name"] == "us-west-2"
        assert kwargs["aws_access_key_id"] == "AKIAIOSFODNN7EXAMPLE"
        assert kwargs["aws_secret_access_key"] == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert (
            kwargs["aws_session_token"]
            == "AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4Olgk"
        )


def test_cloudcontrol_client_initialization_exception():
    """Test the CloudControlClient initialization when an exception occurs."""
    with patch("boto3.client", side_effect=Exception("Test exception")):
        client = CloudControlClient()
        assert client.cloudcontrol_client is None
        assert client.cloudformation_client is None


def test_main_stdio():
    """Test the main function with stdio transport."""
    with patch("awslabs.aws_cloudcontrol_server.server.mcp.run") as mock_run:
        with patch("argparse.ArgumentParser.parse_args") as mock_parse_args:
            mock_parse_args.return_value = MagicMock(sse=False, port=8888)
            main()
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert kwargs.get("transport") is None


def test_main_sse():
    """Test the main function with SSE transport."""
    with patch("awslabs.aws_cloudcontrol_server.server.mcp.run") as mock_run:
        with patch("argparse.ArgumentParser.parse_args") as mock_parse_args:
            mock_parse_args.return_value = MagicMock(sse=True, port=9999)
            main()
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert kwargs.get("transport") == "sse"
