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

"""AWS CloudControl API MCP Server implementation."""

import argparse
import asyncio
import boto3
import botocore.config
import botocore.exceptions
import json
import os
import sys
from loguru import logger
# Try to import from mcp.server.fastmcp, but provide fallbacks for testing
try:
    from mcp.server.fastmcp import Context, FastMCP
except ImportError:
    # Mock implementations for testing without mcp-server-fastmcp
    class Context:
        """Mock Context class for testing."""
        
        def __init__(self, _request_context=None, _fastmcp=None):
            """Initialize the mock context."""
            pass
            
        async def error(self, message=None, **extra):
            """Handle error messages."""
            logger.error(message)
            
        async def info(self, message=None, **extra):
            """Handle info messages."""
            logger.info(message)
            
        async def warning(self, message=None, **extra):
            """Handle warning messages."""
            logger.warning(message)
            
        async def debug(self, message=None, **extra):
            """Handle debug messages."""
            logger.debug(message)
    
    class FastMCP:
        """Mock FastMCP class for testing."""
        
        def __init__(self, name, instructions=None, dependencies=None):
            """Initialize the mock FastMCP."""
            self.name = name
            self.instructions = instructions
            self.dependencies = dependencies
            self.settings = type('Settings', (), {'port': 8888})
            
        def tool(self):
            """Mock tool decorator."""
            def decorator(func):
                return func
            return decorator
            
        def run(self, transport=None):
            """Mock run method."""
            logger.info(f"Mock FastMCP running with transport: {transport}")
from pydantic import Field
from typing import Dict, List, Optional, Union


# Set up logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Initialize FastMCP server
mcp = FastMCP(
    'awslabs.aws-cloudcontrol-mcp-server',
    instructions="""
    # AWS CloudControl API MCP Server

    This server provides tools to interact with AWS CloudControl API capabilities, focusing on standardized resource management across AWS services.

    ## Features
    - Create AWS resources using standardized resource type schemas
    - Get details about specific AWS resources
    - Update existing AWS resources using JSON patch documents
    - Delete AWS resources
    - List resources of a specific type in your AWS account
    - Track and manage resource operation requests

    ## Prerequisites
    1. Have an AWS account with access to AWS CloudControl API
    2. Configure AWS CLI with your credentials and profile
    3. Set AWS_REGION environment variable if not using default

    ## Best Practices
    - Use resource type schemas to understand resource properties
    - Specify idempotency tokens for create, update, and delete operations
    - Track asynchronous operations using request tokens
    - Use IAM roles for enhanced security and longer operation timeouts
    """,
    dependencies=[
        'boto3',
        'pydantic',
    ],
)


class CloudControlClient:
    """AWS CloudControl API client wrapper."""

    def __init__(self):
        """Initialize the AWS CloudControl API client."""
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        self.cloudcontrol_client = None
        self.cloudformation_client = None
        config = botocore.config.Config(
            connect_timeout=15, read_timeout=15, retries={'max_attempts': 3}
        )
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
        try:
            if aws_access_key and aws_secret_key:
                client_args = {
                    'aws_access_key_id': aws_access_key,
                    'aws_secret_access_key': aws_secret_key,
                    'region_name': self.aws_region,
                    'config': config,
                }
                if aws_session_token:
                    client_args['aws_session_token'] = aws_session_token
                self.cloudcontrol_client = boto3.client('cloudcontrol', **client_args)
                self.cloudformation_client = boto3.client('cloudformation', **client_args)
            else:
                self.cloudcontrol_client = boto3.client(
                    'cloudcontrol', region_name=self.aws_region, config=config
                )
                self.cloudformation_client = boto3.client(
                    'cloudformation', region_name=self.aws_region, config=config
                )
            logger.debug(f'AWS CloudControl API client initialized for region {self.aws_region}')
        except Exception as e:
            logger.error(f'Failed to initialize AWS CloudControl API client: {str(e)}')
            self.cloudcontrol_client = None
            self.cloudformation_client = None


# Initialize the CloudControl client
cloudcontrol_client = CloudControlClient()


@mcp.tool()
async def create_resource(
    ctx: Context,
    type_name: str = Field(description='The type name of the resource to create'),
    desired_state: dict = Field(description='JSON object representing the desired state of the resource'),
    role_arn: Optional[str] = Field(default=None, description='Optional IAM role ARN to use for this operation'),
    client_token: Optional[str] = Field(default=None, description='Idempotency token for the request'),
) -> Dict:
    """Create a resource using AWS CloudControl API."""
    if not cloudcontrol_client.cloudcontrol_client:
        error_msg = 'AWS CloudControl API client not initialized'
        await ctx.error(error_msg)
        return {'error': error_msg}
    
    try:
        # Convert desired_state to JSON string if it's a dict
        if isinstance(desired_state, dict):
            desired_state_json = json.dumps(desired_state)
        else:
            desired_state_json = desired_state
            
        # Prepare request parameters
        params = {
            'TypeName': type_name,
            'DesiredState': desired_state_json,
        }
        
        # Add optional parameters if provided
        if role_arn:
            params['RoleArn'] = role_arn
        if client_token:
            params['ClientToken'] = client_token
            
        # Make the API call
        response = await asyncio.to_thread(
            cloudcontrol_client.cloudcontrol_client.create_resource,
            **params
        )
        
        # Return the progress event
        return {
            'ProgressEvent': {
                'EventTime': response['ProgressEvent']['EventTime'].isoformat() if 'EventTime' in response['ProgressEvent'] else None,
                'TypeName': response['ProgressEvent'].get('TypeName'),
                'OperationStatus': response['ProgressEvent'].get('OperationStatus'),
                'Operation': response['ProgressEvent'].get('Operation'),
                'Identifier': response['ProgressEvent'].get('Identifier'),
                'RequestToken': response['ProgressEvent'].get('RequestToken'),
                'StatusMessage': response['ProgressEvent'].get('StatusMessage'),
            }
        }
    except botocore.exceptions.ClientError as e:
        error_msg = f'AWS CloudControl API error: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Error creating resource: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}


@mcp.tool()
async def get_resource(
    ctx: Context,
    type_name: str = Field(description='The type name of the resource'),
    identifier: str = Field(description='The primary identifier of the resource'),
    role_arn: Optional[str] = Field(default=None, description='Optional IAM role ARN to use for this operation'),
) -> Dict:
    """Get details about a resource using AWS CloudControl API."""
    if not cloudcontrol_client.cloudcontrol_client:
        error_msg = 'AWS CloudControl API client not initialized'
        await ctx.error(error_msg)
        return {'error': error_msg}
    
    try:
        # Prepare request parameters
        params = {
            'TypeName': type_name,
            'Identifier': identifier,
        }
        
        # Add optional parameters if provided
        if role_arn:
            params['RoleArn'] = role_arn
            
        # Make the API call
        response = await asyncio.to_thread(
            cloudcontrol_client.cloudcontrol_client.get_resource,
            **params
        )
        
        # Return the resource description
        return {
            'TypeName': response.get('TypeName'),
            'ResourceDescription': {
                'Identifier': response['ResourceDescription'].get('Identifier'),
                'Properties': json.loads(response['ResourceDescription'].get('Properties', '{}')),
            }
        }
    except botocore.exceptions.ClientError as e:
        error_msg = f'AWS CloudControl API error: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Error getting resource: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}


@mcp.tool()
async def update_resource(
    ctx: Context,
    type_name: str = Field(description='The type name of the resource to update'),
    identifier: str = Field(description='The primary identifier of the resource'),
    patch_document: str = Field(description='JSON patch document for the update'),
    role_arn: Optional[str] = Field(default=None, description='Optional IAM role ARN to use for this operation'),
    client_token: Optional[str] = Field(default=None, description='Idempotency token for the request'),
) -> Dict:
    """Update a resource using AWS CloudControl API."""
    if not cloudcontrol_client.cloudcontrol_client:
        error_msg = 'AWS CloudControl API client not initialized'
        await ctx.error(error_msg)
        return {'error': error_msg}
    
    try:
        # Prepare request parameters
        params = {
            'TypeName': type_name,
            'Identifier': identifier,
            'PatchDocument': patch_document,
        }
        
        # Add optional parameters if provided
        if role_arn:
            params['RoleArn'] = role_arn
        if client_token:
            params['ClientToken'] = client_token
            
        # Make the API call
        response = await asyncio.to_thread(
            cloudcontrol_client.cloudcontrol_client.update_resource,
            **params
        )
        
        # Return the progress event
        return {
            'ProgressEvent': {
                'EventTime': response['ProgressEvent']['EventTime'].isoformat() if 'EventTime' in response['ProgressEvent'] else None,
                'TypeName': response['ProgressEvent'].get('TypeName'),
                'OperationStatus': response['ProgressEvent'].get('OperationStatus'),
                'Operation': response['ProgressEvent'].get('Operation'),
                'Identifier': response['ProgressEvent'].get('Identifier'),
                'RequestToken': response['ProgressEvent'].get('RequestToken'),
                'StatusMessage': response['ProgressEvent'].get('StatusMessage'),
            }
        }
    except botocore.exceptions.ClientError as e:
        error_msg = f'AWS CloudControl API error: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Error updating resource: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}


@mcp.tool()
async def delete_resource(
    ctx: Context,
    type_name: str = Field(description='The type name of the resource to delete'),
    identifier: str = Field(description='The primary identifier of the resource'),
    role_arn: Optional[str] = Field(default=None, description='Optional IAM role ARN to use for this operation'),
    client_token: Optional[str] = Field(default=None, description='Idempotency token for the request'),
) -> Dict:
    """Delete a resource using AWS CloudControl API."""
    if not cloudcontrol_client.cloudcontrol_client:
        error_msg = 'AWS CloudControl API client not initialized'
        await ctx.error(error_msg)
        return {'error': error_msg}
    
    try:
        # Prepare request parameters
        params = {
            'TypeName': type_name,
            'Identifier': identifier,
        }
        
        # Add optional parameters if provided
        if role_arn:
            params['RoleArn'] = role_arn
        if client_token:
            params['ClientToken'] = client_token
            
        # Make the API call
        response = await asyncio.to_thread(
            cloudcontrol_client.cloudcontrol_client.delete_resource,
            **params
        )
        
        # Return the progress event
        return {
            'ProgressEvent': {
                'EventTime': response['ProgressEvent']['EventTime'].isoformat() if 'EventTime' in response['ProgressEvent'] else None,
                'TypeName': response['ProgressEvent'].get('TypeName'),
                'OperationStatus': response['ProgressEvent'].get('OperationStatus'),
                'Operation': response['ProgressEvent'].get('Operation'),
                'Identifier': response['ProgressEvent'].get('Identifier'),
                'RequestToken': response['ProgressEvent'].get('RequestToken'),
                'StatusMessage': response['ProgressEvent'].get('StatusMessage'),
            }
        }
    except botocore.exceptions.ClientError as e:
        error_msg = f'AWS CloudControl API error: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Error deleting resource: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}


@mcp.tool()
async def list_resources(
    ctx: Context,
    type_name: str = Field(description='The type name of the resources to list'),
    resource_model: Optional[Dict] = Field(default=None, description='Optional resource model for resources that require additional information'),
    role_arn: Optional[str] = Field(default=None, description='Optional IAM role ARN to use for this operation'),
    next_token: Optional[str] = Field(default=None, description='Token for pagination'),
) -> Dict:
    """List resources of a specific type using AWS CloudControl API."""
    if not cloudcontrol_client.cloudcontrol_client:
        error_msg = 'AWS CloudControl API client not initialized'
        await ctx.error(error_msg)
        return {'error': error_msg}
    
    try:
        # Prepare request parameters
        params = {
            'TypeName': type_name,
        }
        
        # Add optional parameters if provided
        if resource_model:
            if isinstance(resource_model, dict):
                params['ResourceModel'] = json.dumps(resource_model)
            else:
                params['ResourceModel'] = resource_model
        if role_arn:
            params['RoleArn'] = role_arn
        if next_token:
            params['NextToken'] = next_token
            
        # Make the API call
        response = await asyncio.to_thread(
            cloudcontrol_client.cloudcontrol_client.list_resources,
            **params
        )
        
        # Process the resource descriptions
        resource_descriptions = []
        for resource in response.get('ResourceDescriptions', []):
            try:
                properties = json.loads(resource.get('Properties', '{}'))
            except json.JSONDecodeError:
                properties = {}
                
            resource_descriptions.append({
                'Identifier': resource.get('Identifier'),
                'Properties': properties,
            })
        
        # Return the list of resources
        result = {
            'TypeName': response.get('TypeName'),
            'ResourceDescriptions': resource_descriptions,
        }
        
        # Add NextToken if present
        if 'NextToken' in response:
            result['NextToken'] = response['NextToken']
            
        return result
    except botocore.exceptions.ClientError as e:
        error_msg = f'AWS CloudControl API error: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Error listing resources: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}


@mcp.tool()
async def get_resource_request_status(
    ctx: Context,
    request_token: str = Field(description='The request token returned from a resource operation'),
) -> Dict:
    """Get the status of a resource request using AWS CloudControl API."""
    if not cloudcontrol_client.cloudcontrol_client:
        error_msg = 'AWS CloudControl API client not initialized'
        await ctx.error(error_msg)
        return {'error': error_msg}
    
    try:
        # Make the API call
        response = await asyncio.to_thread(
            cloudcontrol_client.cloudcontrol_client.get_resource_request_status,
            RequestToken=request_token
        )
        
        # Return the progress event
        return {
            'ProgressEvent': {
                'EventTime': response['ProgressEvent']['EventTime'].isoformat() if 'EventTime' in response['ProgressEvent'] else None,
                'TypeName': response['ProgressEvent'].get('TypeName'),
                'OperationStatus': response['ProgressEvent'].get('OperationStatus'),
                'Operation': response['ProgressEvent'].get('Operation'),
                'Identifier': response['ProgressEvent'].get('Identifier'),
                'RequestToken': response['ProgressEvent'].get('RequestToken'),
                'StatusMessage': response['ProgressEvent'].get('StatusMessage'),
            }
        }
    except botocore.exceptions.ClientError as e:
        error_msg = f'AWS CloudControl API error: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Error getting resource request status: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}


@mcp.tool()
async def cancel_resource_request(
    ctx: Context,
    request_token: str = Field(description='The request token of the request to cancel'),
) -> Dict:
    """Cancel a resource request using AWS CloudControl API."""
    if not cloudcontrol_client.cloudcontrol_client:
        error_msg = 'AWS CloudControl API client not initialized'
        await ctx.error(error_msg)
        return {'error': error_msg}
    
    try:
        # Make the API call
        response = await asyncio.to_thread(
            cloudcontrol_client.cloudcontrol_client.cancel_resource_request,
            RequestToken=request_token
        )
        
        # Return the progress event
        return {
            'ProgressEvent': {
                'EventTime': response['ProgressEvent']['EventTime'].isoformat() if 'EventTime' in response['ProgressEvent'] else None,
                'TypeName': response['ProgressEvent'].get('TypeName'),
                'OperationStatus': response['ProgressEvent'].get('OperationStatus'),
                'Operation': response['ProgressEvent'].get('Operation'),
                'Identifier': response['ProgressEvent'].get('Identifier'),
                'RequestToken': response['ProgressEvent'].get('RequestToken'),
                'StatusMessage': response['ProgressEvent'].get('StatusMessage'),
            }
        }
    except botocore.exceptions.ClientError as e:
        error_msg = f'AWS CloudControl API error: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Error canceling resource request: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}


@mcp.tool()
async def list_resource_requests(
    ctx: Context,
    resource_request_status_filter: Optional[Dict] = Field(default=None, description='Filter for resource request status'),
    next_token: Optional[str] = Field(default=None, description='Token for pagination'),
) -> Dict:
    """List resource requests using AWS CloudControl API."""
    if not cloudcontrol_client.cloudcontrol_client:
        error_msg = 'AWS CloudControl API client not initialized'
        await ctx.error(error_msg)
        return {'error': error_msg}
    
    try:
        # Prepare request parameters
        params = {}
        
        # Add optional parameters if provided
        if resource_request_status_filter:
            params['ResourceRequestStatusFilter'] = resource_request_status_filter
        if next_token:
            params['NextToken'] = next_token
            
        # Make the API call
        response = await asyncio.to_thread(
            cloudcontrol_client.cloudcontrol_client.list_resource_requests,
            **params
        )
        
        # Process the resource request status summaries
        resource_request_status_summaries = []
        for summary in response.get('ResourceRequestStatusSummaries', []):
            resource_request_status_summaries.append({
                'EventTime': summary['EventTime'].isoformat() if 'EventTime' in summary else None,
                'TypeName': summary.get('TypeName'),
                'OperationStatus': summary.get('OperationStatus'),
                'Operation': summary.get('Operation'),
                'Identifier': summary.get('Identifier'),
                'RequestToken': summary.get('RequestToken'),
                'StatusMessage': summary.get('StatusMessage'),
            })
        
        # Return the list of resource request status summaries
        result = {
            'ResourceRequestStatusSummaries': resource_request_status_summaries,
        }
        
        # Add NextToken if present
        if 'NextToken' in response:
            result['NextToken'] = response['NextToken']
            
        return result
    except botocore.exceptions.ClientError as e:
        error_msg = f'AWS CloudControl API error: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Error listing resource requests: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}


@mcp.tool()
async def list_resource_types(
    ctx: Context,
    filters: Optional[Dict] = Field(default=None, description='Optional filters for resource types'),
) -> Dict:
    """List available resource types in AWS CloudControl API."""
    if not cloudcontrol_client.cloudformation_client:
        error_msg = 'AWS CloudFormation client not initialized'
        await ctx.error(error_msg)
        return {'error': error_msg}
    
    try:
        # Prepare request parameters
        params = {}
        
        # Add optional parameters if provided
        if filters:
            params['Filters'] = filters
            
        # Make the API call to CloudFormation (which manages resource types)
        response = await asyncio.to_thread(
            cloudcontrol_client.cloudformation_client.list_types,
            **params
        )
        
        # Process the type summaries
        type_summaries = []
        for summary in response.get('TypeSummaries', []):
            type_summaries.append({
                'TypeName': summary.get('TypeName'),
                'TypeArn': summary.get('TypeArn'),
                'Description': summary.get('Description'),
                'ProvisioningType': summary.get('ProvisioningType'),
                'DeprecatedStatus': summary.get('DeprecatedStatus'),
                'DefaultVersionId': summary.get('DefaultVersionId'),
                'PublicVersionNumber': summary.get('PublicVersionNumber'),
                'PublisherId': summary.get('PublisherId'),
                'PublisherName': summary.get('PublisherName'),
                'PublisherIdentity': summary.get('PublisherIdentity'),
                'OriginalTypeName': summary.get('OriginalTypeName'),
                'LastUpdated': summary['LastUpdated'].isoformat() if 'LastUpdated' in summary else None,
                'LatestPublicVersion': summary.get('LatestPublicVersion'),
                'PublisherProfile': summary.get('PublisherProfile'),
                'IsActivated': summary.get('IsActivated'),
                'Visibility': summary.get('Visibility'),
                'SourceUrl': summary.get('SourceUrl'),
                'DocumentationUrl': summary.get('DocumentationUrl'),
                'Type': summary.get('Type'),
            })
        
        # Return the list of resource types
        result = {
            'TypeSummaries': type_summaries,
        }
        
        # Add NextToken if present
        if 'NextToken' in response:
            result['NextToken'] = response['NextToken']
            
        return result
    except botocore.exceptions.ClientError as e:
        error_msg = f'AWS CloudFormation API error: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Error listing resource types: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {'error': error_msg}


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for AWS CloudControl API'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    args = parser.parse_args()
    logger.info('Starting AWS CloudControl API MCP Server')
    if args.sse:
        logger.info(f'Using SSE transport on port {args.port}')
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        logger.info('Using standard stdio transport')
        mcp.run()


if __name__ == '__main__':
    main()
