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
"""Integration tests for AWS CloudControl API MCP Server."""

import asyncio
import json
import logging
import os
import pytest
import time
import uuid
from datetime import datetime
from awslabs.aws_cloudcontrol_server.server import (
    create_resource,
    get_resource,
    update_resource,
    delete_resource,
    list_resources,
    get_resource_request_status,
    cancel_resource_request,
    list_resource_requests,
    list_resource_types,
)
from mcp.server.fastmcp import Context


# Set up a logger instead of using print for sensitive data
logger = logging.getLogger('integration_tests')
logger.setLevel(logging.INFO)
# Only log to console during development, not in production
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class DummyContext(Context):
    """Dummy context for testing."""

    async def error(self, message=None, **extra):
        """Handle error messages for DummyContext."""
        logger.error(message)

    async def run_in_threadpool(self, func, *args, **kwargs):
        """Run a function in a threadpool."""
        return func(*args, **kwargs)


@pytest.fixture
def ctx():
    """Create a dummy context for testing."""
    return DummyContext(_request_context=None, _fastmcp=None)


@pytest.fixture
def test_resource_prefix():
    """Generate a unique prefix for test resources."""
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    return f"test-{timestamp}-{unique_id}"


async def wait_for_operation_completion(ctx, request_token, timeout=300, interval=5):
    """Wait for a CloudControl API operation to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        status_result = await get_resource_request_status(ctx, request_token=request_token)
        
        if 'error' in status_result:
            logger.error(f"Error checking operation status: {status_result['error']}")
            return status_result
            
        operation_status = status_result['ProgressEvent'].get('OperationStatus')
        
        if operation_status == 'SUCCESS':
            logger.info(f"Operation completed successfully after {time.time() - start_time:.1f} seconds")
            return status_result
        elif operation_status == 'FAILED':
            logger.error(f"Operation failed: {status_result['ProgressEvent'].get('StatusMessage')}")
            return status_result
        elif operation_status == 'CANCELED':
            logger.warning(f"Operation was canceled")
            return status_result
            
        logger.info(f"Operation in progress ({operation_status}), waiting {interval} seconds...")
        await asyncio.sleep(interval)
        
    logger.error(f"Operation timed out after {timeout} seconds")
    return {'error': f'Operation timed out after {timeout} seconds'}


@pytest.mark.skipif(
    not (os.environ.get('AWS_ACCESS_KEY_ID') or os.environ.get('AWS_PROFILE')),
    reason='AWS credentials not set',
)
@pytest.mark.asyncio
async def test_list_resource_types(ctx):
    """Test listing available resource types."""
    logger.info('\n=== list_resource_types ===')
    
    # List resource types with no filters
    result = await list_resource_types(ctx)
    
    if 'error' in result:
        logger.error(f"Error listing resource types: {result['error']}")
        assert False, f"Failed to list resource types: {result['error']}"
    
    type_summaries = result.get('TypeSummaries', [])
    logger.info(f"Found {len(type_summaries)} resource types")
    
    # Log a sample of resource types (first 5)
    for i, type_summary in enumerate(type_summaries[:5]):
        logger.info(f"Resource Type {i+1}: {type_summary.get('TypeName')} - {type_summary.get('Description', 'No description')}")
    
    # Verify we have some resource types
    assert len(type_summaries) > 0, "No resource types found"
    
    # Check if common resource types are available
    common_types = ["AWS::Logs::LogGroup", "AWS::SSM::Parameter", "AWS::SNS::Topic"]
    found_types = [summary.get('TypeName') for summary in type_summaries]
    
    for common_type in common_types:
        if common_type in found_types:
            logger.info(f"Found common resource type: {common_type}")
        else:
            logger.warning(f"Common resource type not found: {common_type}")


@pytest.mark.skipif(
    not (os.environ.get('AWS_ACCESS_KEY_ID') or os.environ.get('AWS_PROFILE')),
    reason='AWS credentials not set',
)
@pytest.mark.asyncio
async def test_logs_loggroup_lifecycle(ctx, test_resource_prefix):
    """Test the complete lifecycle of an AWS::Logs::LogGroup resource."""
    logger.info('\n=== test_logs_loggroup_lifecycle ===')
    
    # Define resource properties
    log_group_name = f"{test_resource_prefix}-loggroup"
    retention_days = 7
    
    # Step 1: Create the log group
    logger.info(f"Creating log group: {log_group_name}")
    create_result = await create_resource(
        ctx,
        type_name="AWS::Logs::LogGroup",
        desired_state={
            "LogGroupName": log_group_name,
            "RetentionInDays": retention_days
        },
        client_token=f"{test_resource_prefix}-create"
    )
    
    if 'error' in create_result:
        logger.error(f"Error creating log group: {create_result['error']}")
        assert False, f"Failed to create log group: {create_result['error']}"
    
    request_token = create_result['ProgressEvent'].get('RequestToken')
    logger.info(f"Create operation initiated with request token: {request_token}")
    
    # Wait for the create operation to complete
    status_result = await wait_for_operation_completion(ctx, request_token)
    if 'error' in status_result:
        assert False, f"Create operation failed or timed out: {status_result['error']}"
    
    # Step 2: Get the log group details
    logger.info(f"Getting log group details: {log_group_name}")
    get_result = await get_resource(
        ctx,
        type_name="AWS::Logs::LogGroup",
        identifier=log_group_name
    )
    
    if 'error' in get_result:
        logger.error(f"Error getting log group: {get_result['error']}")
        # Try to clean up
        await delete_resource(ctx, type_name="AWS::Logs::LogGroup", identifier=log_group_name)
        assert False, f"Failed to get log group: {get_result['error']}"
    
    # Verify the log group properties
    properties = get_result['ResourceDescription']['Properties']
    logger.info(f"Log group properties: {json.dumps(properties, indent=2)}")
    assert properties.get('LogGroupName') == log_group_name, "Log group name doesn't match"
    assert properties.get('RetentionInDays') == retention_days, "Retention days doesn't match"
    
    # Step 3: Update the log group
    new_retention_days = 14
    logger.info(f"Updating log group retention to {new_retention_days} days")
    patch_document = json.dumps([
        {
            "op": "replace",
            "path": "/RetentionInDays",
            "value": new_retention_days
        }
    ])
    
    update_result = await update_resource(
        ctx,
        type_name="AWS::Logs::LogGroup",
        identifier=log_group_name,
        patch_document=patch_document,
        client_token=f"{test_resource_prefix}-update"
    )
    
    if 'error' in update_result:
        logger.error(f"Error updating log group: {update_result['error']}")
        # Try to clean up
        await delete_resource(ctx, type_name="AWS::Logs::LogGroup", identifier=log_group_name)
        assert False, f"Failed to update log group: {update_result['error']}"
    
    request_token = update_result['ProgressEvent'].get('RequestToken')
    logger.info(f"Update operation initiated with request token: {request_token}")
    
    # Wait for the update operation to complete
    status_result = await wait_for_operation_completion(ctx, request_token)
    if 'error' in status_result:
        # Try to clean up
        await delete_resource(ctx, type_name="AWS::Logs::LogGroup", identifier=log_group_name)
        assert False, f"Update operation failed or timed out: {status_result['error']}"
    
    # Verify the update
    get_result = await get_resource(
        ctx,
        type_name="AWS::Logs::LogGroup",
        identifier=log_group_name
    )
    
    if 'error' in get_result:
        logger.error(f"Error getting updated log group: {get_result['error']}")
        # Try to clean up
        await delete_resource(ctx, type_name="AWS::Logs::LogGroup", identifier=log_group_name)
        assert False, f"Failed to get updated log group: {get_result['error']}"
    
    # Verify the updated properties
    properties = get_result['ResourceDescription']['Properties']
    logger.info(f"Updated log group properties: {json.dumps(properties, indent=2)}")
    assert properties.get('RetentionInDays') == new_retention_days, "Updated retention days doesn't match"
    
    # Step 4: List log groups
    logger.info("Listing log groups")
    list_result = await list_resources(
        ctx,
        type_name="AWS::Logs::LogGroup"
    )
    
    if 'error' in list_result:
        logger.error(f"Error listing log groups: {list_result['error']}")
        # Try to clean up
        await delete_resource(ctx, type_name="AWS::Logs::LogGroup", identifier=log_group_name)
        assert False, f"Failed to list log groups: {list_result['error']}"
    
    resource_descriptions = list_result.get('ResourceDescriptions', [])
    logger.info(f"Found {len(resource_descriptions)} log groups")
    
    # Check if our log group is in the list
    found = False
    for resource in resource_descriptions:
        if resource.get('Identifier') == log_group_name:
            found = True
            logger.info(f"Found our test log group in the list")
            break
    
    assert found, "Our test log group was not found in the list"
    
    # Step 5: Delete the log group
    logger.info(f"Deleting log group: {log_group_name}")
    delete_result = await delete_resource(
        ctx,
        type_name="AWS::Logs::LogGroup",
        identifier=log_group_name,
        client_token=f"{test_resource_prefix}-delete"
    )
    
    if 'error' in delete_result:
        logger.error(f"Error deleting log group: {delete_result['error']}")
        assert False, f"Failed to delete log group: {delete_result['error']}"
    
    request_token = delete_result['ProgressEvent'].get('RequestToken')
    logger.info(f"Delete operation initiated with request token: {request_token}")
    
    # Wait for the delete operation to complete
    status_result = await wait_for_operation_completion(ctx, request_token)
    if 'error' in status_result:
        assert False, f"Delete operation failed or timed out: {status_result['error']}"
    
    logger.info("Log group lifecycle test completed successfully")


@pytest.mark.skipif(
    not (os.environ.get('AWS_ACCESS_KEY_ID') or os.environ.get('AWS_PROFILE')),
    reason='AWS credentials not set',
)
@pytest.mark.asyncio
async def test_ssm_parameter_lifecycle(ctx, test_resource_prefix):
    """Test the complete lifecycle of an AWS::SSM::Parameter resource."""
    logger.info('\n=== test_ssm_parameter_lifecycle ===')
    
    # Define resource properties
    parameter_name = f"/{test_resource_prefix}/test-parameter"
    parameter_type = "String"
    parameter_value = "test-value-1"
    parameter_description = "Test parameter created by integration tests"
    
    # Step 1: Create the parameter
    logger.info(f"Creating SSM parameter: {parameter_name}")
    create_result = await create_resource(
        ctx,
        type_name="AWS::SSM::Parameter",
        desired_state={
            "Name": parameter_name,
            "Type": parameter_type,
            "Value": parameter_value,
            "Description": parameter_description
        },
        client_token=f"{test_resource_prefix}-param-create"
    )
    
    if 'error' in create_result:
        logger.error(f"Error creating SSM parameter: {create_result['error']}")
        assert False, f"Failed to create SSM parameter: {create_result['error']}"
    
    request_token = create_result['ProgressEvent'].get('RequestToken')
    logger.info(f"Create operation initiated with request token: {request_token}")
    
    # Wait for the create operation to complete
    status_result = await wait_for_operation_completion(ctx, request_token)
    if 'error' in status_result:
        assert False, f"Create operation failed or timed out: {status_result['error']}"
    
    # Step 2: Get the parameter details
    logger.info(f"Getting SSM parameter details: {parameter_name}")
    get_result = await get_resource(
        ctx,
        type_name="AWS::SSM::Parameter",
        identifier=parameter_name
    )
    
    if 'error' in get_result:
        logger.error(f"Error getting SSM parameter: {get_result['error']}")
        # Try to clean up
        await delete_resource(ctx, type_name="AWS::SSM::Parameter", identifier=parameter_name)
        assert False, f"Failed to get SSM parameter: {get_result['error']}"
    
    # Verify the parameter properties
    properties = get_result['ResourceDescription']['Properties']
    logger.info(f"SSM parameter properties: Name={properties.get('Name')}, Type={properties.get('Type')}, Description={properties.get('Description')}")
    assert properties.get('Name') == parameter_name, "Parameter name doesn't match"
    assert properties.get('Type') == parameter_type, "Parameter type doesn't match"
    assert properties.get('Description') == parameter_description, "Parameter description doesn't match"
    # Note: We don't log the actual value for security reasons
    
    # Step 3: Update the parameter
    new_parameter_value = "test-value-2"
    logger.info(f"Updating SSM parameter value")
    patch_document = json.dumps([
        {
            "op": "replace",
            "path": "/Value",
            "value": new_parameter_value
        }
    ])
    
    update_result = await update_resource(
        ctx,
        type_name="AWS::SSM::Parameter",
        identifier=parameter_name,
        patch_document=patch_document,
        client_token=f"{test_resource_prefix}-param-update"
    )
    
    if 'error' in update_result:
        logger.error(f"Error updating SSM parameter: {update_result['error']}")
        # Try to clean up
        await delete_resource(ctx, type_name="AWS::SSM::Parameter", identifier=parameter_name)
        assert False, f"Failed to update SSM parameter: {update_result['error']}"
    
    request_token = update_result['ProgressEvent'].get('RequestToken')
    logger.info(f"Update operation initiated with request token: {request_token}")
    
    # Wait for the update operation to complete
    status_result = await wait_for_operation_completion(ctx, request_token)
    if 'error' in status_result:
        # Try to clean up
        await delete_resource(ctx, type_name="AWS::SSM::Parameter", identifier=parameter_name)
        assert False, f"Update operation failed or timed out: {status_result['error']}"
    
    # Step 4: Delete the parameter
    logger.info(f"Deleting SSM parameter: {parameter_name}")
    delete_result = await delete_resource(
        ctx,
        type_name="AWS::SSM::Parameter",
        identifier=parameter_name,
        client_token=f"{test_resource_prefix}-param-delete"
    )
    
    if 'error' in delete_result:
        logger.error(f"Error deleting SSM parameter: {delete_result['error']}")
        assert False, f"Failed to delete SSM parameter: {delete_result['error']}"
    
    request_token = delete_result['ProgressEvent'].get('RequestToken')
    logger.info(f"Delete operation initiated with request token: {request_token}")
    
    # Wait for the delete operation to complete
    status_result = await wait_for_operation_completion(ctx, request_token)
    if 'error' in status_result:
        assert False, f"Delete operation failed or timed out: {status_result['error']}"
    
    logger.info("SSM parameter lifecycle test completed successfully")


@pytest.mark.skipif(
    not (os.environ.get('AWS_ACCESS_KEY_ID') or os.environ.get('AWS_PROFILE')),
    reason='AWS credentials not set',
)
@pytest.mark.asyncio
async def test_resource_request_management(ctx, test_resource_prefix):
    """Test resource request management operations."""
    logger.info('\n=== test_resource_request_management ===')
    
    # Step 1: Create a resource to generate a request
    log_group_name = f"{test_resource_prefix}-request-test"
    logger.info(f"Creating log group for request management test: {log_group_name}")
    
    create_result = await create_resource(
        ctx,
        type_name="AWS::Logs::LogGroup",
        desired_state={
            "LogGroupName": log_group_name,
            "RetentionInDays": 1
        },
        client_token=f"{test_resource_prefix}-request-create"
    )
    
    if 'error' in create_result:
        logger.error(f"Error creating log group: {create_result['error']}")
        assert False, f"Failed to create log group: {create_result['error']}"
    
    request_token = create_result['ProgressEvent'].get('RequestToken')
    logger.info(f"Create operation initiated with request token: {request_token}")
    
    # Step 2: Get the request status
    logger.info(f"Getting request status for token: {request_token}")
    status_result = await get_resource_request_status(ctx, request_token=request_token)
    
    if 'error' in status_result:
        logger.error(f"Error getting request status: {status_result['error']}")
        # Try to clean up
        await delete_resource(ctx, type_name="AWS::Logs::LogGroup", identifier=log_group_name)
        assert False, f"Failed to get request status: {status_result['error']}"
    
    progress_event = status_result.get('ProgressEvent', {})
    logger.info(f"Request status: {progress_event.get('OperationStatus')}")
    logger.info(f"Operation: {progress_event.get('Operation')}")
    logger.info(f"Type name: {progress_event.get('TypeName')}")
    logger.info(f"Identifier: {progress_event.get('Identifier')}")
    
    # Step 3: List resource requests
    logger.info("Listing resource requests")
    list_result = await list_resource_requests(ctx)
    
    if 'error' in list_result:
        logger.error(f"Error listing resource requests: {list_result['error']}")
        # Try to clean up
        await delete_resource(ctx, type_name="AWS::Logs::LogGroup", identifier=log_group_name)
        assert False, f"Failed to list resource requests: {list_result['error']}"
    
    request_summaries = list_result.get('ResourceRequestStatusSummaries', [])
    logger.info(f"Found {len(request_summaries)} resource requests")
    
    # Check if our request is in the list
    found = False
    for summary in request_summaries:
        if summary.get('RequestToken') == request_token:
            found = True
            logger.info(f"Found our test request in the list")
            break
    
    assert found, "Our test request was not found in the list"
    
    # Wait for the create operation to complete
    await wait_for_operation_completion(ctx, request_token)
    
    # Step 4: Clean up by deleting the log group
    logger.info(f"Cleaning up by deleting log group: {log_group_name}")
    delete_result = await delete_resource(
        ctx,
        type_name="AWS::Logs::LogGroup",
        identifier=log_group_name,
        client_token=f"{test_resource_prefix}-request-delete"
    )
    
    if 'error' in delete_result:
        logger.error(f"Error deleting log group: {delete_result['error']}")
        assert False, f"Failed to delete log group: {delete_result['error']}"
    
    delete_request_token = delete_result['ProgressEvent'].get('RequestToken')
    
    # Wait for the delete operation to complete
    await wait_for_operation_completion(ctx, delete_request_token)
    
    logger.info("Resource request management test completed successfully")


@pytest.mark.skipif(
    not (os.environ.get('AWS_ACCESS_KEY_ID') or os.environ.get('AWS_PROFILE')),
    reason='AWS credentials not set',
)
@pytest.mark.asyncio
async def test_idempotency_with_client_token(ctx, test_resource_prefix):
    """Test idempotency using client tokens."""
    logger.info('\n=== test_idempotency_with_client_token ===')
    
    # Define resource properties
    log_group_name = f"{test_resource_prefix}-idempotency-test"
    client_token = f"{test_resource_prefix}-idempotent-create"
    
    # Step 1: Create a log group with a client token
    logger.info(f"Creating log group with client token: {log_group_name}")
    create_result_1 = await create_resource(
        ctx,
        type_name="AWS::Logs::LogGroup",
        desired_state={
            "LogGroupName": log_group_name,
            "RetentionInDays": 1
        },
        client_token=client_token
    )
    
    if 'error' in create_result_1:
        logger.error(f"Error creating log group (first attempt): {create_result_1['error']}")
        assert False, f"Failed to create log group (first attempt): {create_result_1['error']}"
    
    request_token_1 = create_result_1['ProgressEvent'].get('RequestToken')
    logger.info(f"First create operation initiated with request token: {request_token_1}")
    
    # Wait for the first create operation to complete
    await wait_for_operation_completion(ctx, request_token_1)
    
    # Step 2: Try to create the same log group with the same client token
    logger.info(f"Creating log group with same client token (should be idempotent)")
    create_result_2 = await create_resource(
        ctx,
        type_name="AWS::Logs::LogGroup",
        desired_state={
            "LogGroupName": log_group_name,
            "RetentionInDays": 1
        },
        client_token=client_token
    )
    
    if 'error' in create_result_2:
        logger.error(f"Error in idempotent create: {create_result_2['error']}")
        # Try to clean up
        await delete_resource(ctx, type_name="AWS::Logs::LogGroup", identifier=log_group_name)
        assert False, f"Failed in idempotent create: {create_result_2['error']}"
    
    request_token_2 = create_result_2['ProgressEvent'].get('RequestToken')
    logger.info(f"Second create operation initiated with request token: {request_token_2}")
    
    # Wait for the second create operation to complete
    await wait_for_operation_completion(ctx, request_token_2)
    
    # Step 3: Clean up by deleting the log group
    logger.info(f"Cleaning up by deleting log group: {log_group_name}")
    delete_result = await delete_resource(
        ctx,
        type_name="AWS::Logs::LogGroup",
        identifier=log_group_name,
        client_token=f"{test_resource_prefix}-idempotent-delete"
    )
    
    if 'error' in delete_result:
        logger.error(f"Error deleting log group: {delete_result['error']}")
        assert False, f"Failed to delete log group: {delete_result['error']}"
    
    delete_request_token = delete_result['ProgressEvent'].get('RequestToken')
    
    # Wait for the delete operation to complete
    await wait_for_operation_completion(ctx, delete_request_token)
    
    logger.info("Idempotency test completed successfully")


async def main():
    """Run integration tests for AWS CloudControl MCP server."""
    if not (os.environ.get('AWS_ACCESS_KEY_ID') or os.environ.get('AWS_PROFILE')):
        logger.error('AWS credentials not set.')
        return
    if not os.environ.get('AWS_REGION'):
        logger.error('AWS_REGION not set.')
        return
    
    ctx = DummyContext(_request_context=None, _fastmcp=None)
    test_resource_prefix = f"test-{int(time.time())}-{str(uuid.uuid4())[:8]}"
    
    try:
        # Run the tests
        await test_list_resource_types(ctx)
        await test_logs_loggroup_lifecycle(ctx, test_resource_prefix)
        await test_ssm_parameter_lifecycle(ctx, test_resource_prefix)
        await test_resource_request_management(ctx, test_resource_prefix)
        await test_idempotency_with_client_token(ctx, test_resource_prefix)
        
        logger.info("All integration tests completed successfully!")
    except Exception as e:
        logger.error(f"Integration tests failed: {str(e)}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
