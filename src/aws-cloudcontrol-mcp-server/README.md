# AWS CloudControl MCP Server

Model Context Protocol (MCP) server for AWS CloudControl API

This MCP server provides tools to access AWS CloudControl API capabilities, focusing on standardized resource management across AWS services.

## What is AWS CloudControl API?

[AWS CloudControl API](https://docs.aws.amazon.com/cloudcontrolapi/latest/userguide/what-is-cloudcontrolapi.html) provides a standardized set of APIs to create, read, update, delete, and list (CRUDL) resources across AWS services. It uses the same resource model as AWS CloudFormation, allowing you to manage resources using a consistent interface regardless of the underlying service.

Key benefits of CloudControl API:
- **Unified Interface**: Manage resources across different AWS services with a consistent API
- **Standardized Operations**: Create, read, update, delete, and list resources using the same patterns
- **Resource Type Schema**: Leverage the same resource type schemas used by CloudFormation
- **Asynchronous Operations**: Track long-running operations with request tokens
- **Idempotency**: Use client tokens to ensure operations are only executed once

## Features

- **Create Resources**: Create AWS resources using standardized resource type schemas
- **Read Resources**: Get details about specific AWS resources
- **Update Resources**: Update existing AWS resources using JSON patch documents
- **Delete Resources**: Delete AWS resources
- **List Resources**: Discover resources of a specific type in your AWS account
- **Track Operations**: Monitor the status of asynchronous resource operations
- **Cancel Operations**: Cancel in-progress resource operations
- **List Requests**: List active resource operation requests

## How This MCP Server Helps

The AWS CloudControl MCP Server simplifies resource management across AWS services by:

1. **Providing a Consistent Interface**: Manage different AWS resources with the same patterns
2. **Simplifying Resource Operations**: No need to learn service-specific APIs for basic operations
3. **Enabling Infrastructure as Code**: Easily integrate with infrastructure as code workflows
4. **Facilitating Resource Discovery**: Find and inspect resources across your AWS account
5. **Supporting Asynchronous Operations**: Track and manage long-running operations
6. **Ensuring Idempotency**: Prevent duplicate resource creation with client tokens
7. **Enhancing Error Handling**: Get standardized error responses across services

## Prerequisites

### Requirements

1. Have an AWS account with access to AWS CloudControl API
2. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
3. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Installation

Here are the ways you can work with the AWS CloudControl MCP server:

## Configuration

Configure the server in your MCP configuration file. Here are some ways you can work with MCP across AWS, and we'll be adding support to more products soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.aws-cloudcontrol-mcp-server": {
        "command": "uvx",
        "args": ["awslabs.aws-cloudcontrol-mcp-server@latest"],
        "env": {
          "AWS_PROFILE": "your-aws-profile",
          "AWS_REGION": "us-east-1",
          "FASTMCP_LOG_LEVEL": "ERROR"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

### Using Temporary Credentials

For temporary credentials (such as those from AWS STS, IAM roles, or federation):

```json
{
  "mcpServers": {
    "awslabs.aws-cloudcontrol-mcp-server": {
        "command": "uvx",
        "args": ["awslabs.aws-cloudcontrol-mcp-server@latest"],
        "env": {
          "AWS_ACCESS_KEY_ID": "your-temporary-access-key",
          "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key",
          "AWS_SESSION_TOKEN": "your-session-token",
          "AWS_REGION": "us-east-1",
          "FASTMCP_LOG_LEVEL": "ERROR"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

### Docker Configuration

After building with `docker build -t awslabs/aws-cloudcontrol-mcp-server .`:

```json
{
  "mcpServers": {
    "awslabs.aws-cloudcontrol-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "-i",
          "awslabs/aws-cloudcontrol-mcp-server"
        ],
        "env": {
          "AWS_PROFILE": "your-aws-profile",
          "AWS_REGION": "us-east-1"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

### Docker with Temporary Credentials

```json
{
  "mcpServers": {
    "awslabs.aws-cloudcontrol-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "-i",
          "awslabs/aws-cloudcontrol-mcp-server"
        ],
        "env": {
          "AWS_ACCESS_KEY_ID": "your-temporary-access-key",
          "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key",
          "AWS_SESSION_TOKEN": "your-session-token",
          "AWS_REGION": "us-east-1"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

### Environment Variables

- `AWS_PROFILE`: AWS CLI profile to use for credentials
- `AWS_REGION`: AWS region to use (default: us-east-1)
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`: Explicit AWS credentials (alternative to AWS_PROFILE)
- `AWS_SESSION_TOKEN`: Session token for temporary credentials (used with AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
- `FASTMCP_LOG_LEVEL`: Logging level (ERROR, WARNING, INFO, DEBUG)

## Tools

The server exposes the following tools through the MCP interface:

### create_resource

Create a new AWS resource using AWS CloudControl API.

```python
create_resource(type_name: str, desired_state: dict, role_arn: str = None, client_token: str = None) -> dict
```

### get_resource

Get details about a specific AWS resource.

```python
get_resource(type_name: str, identifier: str, role_arn: str = None) -> dict
```

### update_resource

Update an existing AWS resource using a JSON patch document.

```python
update_resource(type_name: str, identifier: str, patch_document: str, role_arn: str = None, client_token: str = None) -> dict
```

### delete_resource

Delete an AWS resource.

```python
delete_resource(type_name: str, identifier: str, role_arn: str = None, client_token: str = None) -> dict
```

### list_resources

List AWS resources of a specific type.

```python
list_resources(type_name: str, resource_model: dict = None, role_arn: str = None, next_token: str = None) -> dict
```

### get_resource_request_status

Get the status of a resource operation request.

```python
get_resource_request_status(request_token: str) -> dict
```

### cancel_resource_request

Cancel an in-progress resource operation request.

```python
cancel_resource_request(request_token: str) -> dict
```

### list_resource_requests

List active resource operation requests.

```python
list_resource_requests(resource_request_status_filter: dict = None, next_token: str = None) -> dict
```

### list_resource_types

List available resource types in AWS CloudControl API.

```python
list_resource_types(filters: dict = None) -> dict
```

## Practical Examples

### AWS::SecretsManager::Secret Example

Create and manage Secrets Manager secrets:

```python
# Create a Secrets Manager secret
secret_name = "my-application-secret"
secret_value = {"username": "admin", "password": "secure-password"}

create_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="create_resource",
    arguments={
        "type_name": "AWS::SecretsManager::Secret",
        "desired_state": {
            "Name": secret_name,
            "Description": "API credentials for external service",
            "SecretString": json.dumps(secret_value),
            "Tags": [
                {
                    "Key": "Environment",
                    "Value": "Production"
                }
            ]
        },
        "client_token": "create-secret-token"
    }
)

# Get the request token to track the operation
request_token = create_result['ProgressEvent']['RequestToken']

# Check the operation status and get the secret ARN
status_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="get_resource_request_status",
    arguments={"request_token": request_token}
)

# Extract the secret ARN from the status result
secret_arn = status_result['ProgressEvent']['Identifier']

# Get the secret details
get_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="get_resource",
    arguments={
        "type_name": "AWS::SecretsManager::Secret",
        "identifier": secret_arn
    }
)

# Update the secret description
patch_document = [
    {
        "op": "replace",
        "path": "/Description",
        "value": "Updated API credentials for external service"
    }
]

update_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="update_resource",
    arguments={
        "type_name": "AWS::SecretsManager::Secret",
        "identifier": secret_arn,
        "patch_document": json.dumps(patch_document),
        "client_token": "update-secret-token"
    }
)

# Update the secret value
new_secret_value = {"username": "admin", "password": "new-secure-password"}
patch_document = [
    {
        "op": "replace",
        "path": "/SecretString",
        "value": json.dumps(new_secret_value)
    }
]

update_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="update_resource",
    arguments={
        "type_name": "AWS::SecretsManager::Secret",
        "identifier": secret_arn,
        "patch_document": json.dumps(patch_document),
        "client_token": "update-secret-value-token"
    }
)

# Delete the secret when no longer needed
delete_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="delete_resource",
    arguments={
        "type_name": "AWS::SecretsManager::Secret",
        "identifier": secret_arn,
        "client_token": "delete-secret-token"
    }
)
```

### AWS::Logs::LogGroup Example

Create and manage CloudWatch Log Groups:

```python
# Create a CloudWatch Log Group
create_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="create_resource",
    arguments={
        "type_name": "AWS::Logs::LogGroup",
        "desired_state": {
            "LogGroupName": "/aws/lambda/my-function",
            "RetentionInDays": 7
        },
        "client_token": "create-log-group-token"
    }
)

# Get the request token to track the operation
request_token = create_result['ProgressEvent']['RequestToken']

# Check the operation status
status_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="get_resource_request_status",
    arguments={"request_token": request_token}
)

# Get the log group details
get_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="get_resource",
    arguments={
        "type_name": "AWS::Logs::LogGroup",
        "identifier": "/aws/lambda/my-function"
    }
)

# Update the Log Group retention period
patch_document = [
    {
        "op": "replace",
        "path": "/RetentionInDays",
        "value": 14
    }
]

update_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="update_resource",
    arguments={
        "type_name": "AWS::Logs::LogGroup",
        "identifier": "/aws/lambda/my-function",
        "patch_document": json.dumps(patch_document),
        "client_token": "update-log-group-token"
    }
)

# Delete the log group when no longer needed
delete_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="delete_resource",
    arguments={
        "type_name": "AWS::Logs::LogGroup",
        "identifier": "/aws/lambda/my-function",
        "client_token": "delete-log-group-token"
    }
)
```

### AWS::SSM::Parameter Example

Create and manage SSM Parameters:

```python
# Create an SSM Parameter
create_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="create_resource",
    arguments={
        "type_name": "AWS::SSM::Parameter",
        "desired_state": {
            "Name": "/app/config/api-key",
            "Type": "String",
            "Value": "my-api-key-value",
            "Description": "API Key for external service"
        },
        "client_token": "create-parameter-token"
    }
)

# Get the parameter details
get_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="get_resource",
    arguments={
        "type_name": "AWS::SSM::Parameter",
        "identifier": "/app/config/api-key"
    }
)

# Update the SSM Parameter value
patch_document = [
    {
        "op": "replace",
        "path": "/Value",
        "value": "updated-api-key-value"
    }
]

update_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="update_resource",
    arguments={
        "type_name": "AWS::SSM::Parameter",
        "identifier": "/app/config/api-key",
        "patch_document": json.dumps(patch_document),
        "client_token": "update-parameter-token"
    }
)

# Delete the parameter when no longer needed
delete_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="delete_resource",
    arguments={
        "type_name": "AWS::SSM::Parameter",
        "identifier": "/app/config/api-key",
        "client_token": "delete-parameter-token"
    }
)
```

### AWS::SNS::Topic Example

Create and manage SNS Topics:

```python
# Create an SNS Topic
create_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="create_resource",
    arguments={
        "type_name": "AWS::SNS::Topic",
        "desired_state": {
            "TopicName": "notification-topic",
            "DisplayName": "System Notifications",
            "Tags": [
                {
                    "Key": "Environment",
                    "Value": "Production"
                }
            ]
        },
        "client_token": "create-topic-token"
    }
)

# Get the topic ARN from the operation result
status_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="get_resource_request_status",
    arguments={"request_token": create_result['ProgressEvent']['RequestToken']}
)
topic_arn = status_result['ProgressEvent']['Identifier']

# Update the topic display name
patch_document = [
    {
        "op": "replace",
        "path": "/DisplayName",
        "value": "Updated System Notifications"
    }
]

update_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="update_resource",
    arguments={
        "type_name": "AWS::SNS::Topic",
        "identifier": topic_arn,
        "patch_document": json.dumps(patch_document),
        "client_token": "update-topic-token"
    }
)
```

### AWS::S3::Bucket Example

Create and manage S3 Buckets:

```python
# Create an S3 Bucket with security settings
create_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="create_resource",
    arguments={
        "type_name": "AWS::S3::Bucket",
        "desired_state": {
            "BucketName": "my-secure-bucket",
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True
            }
        },
        "client_token": "create-bucket-token"
    }
)

# Enable versioning on the bucket
patch_document = [
    {
        "op": "add",
        "path": "/VersioningConfiguration",
        "value": {
            "Status": "Enabled"
        }
    }
]

update_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="update_resource",
    arguments={
        "type_name": "AWS::S3::Bucket",
        "identifier": "my-secure-bucket",
        "patch_document": json.dumps(patch_document),
        "client_token": "update-bucket-token"
    }
)
```

### AWS::IAM::Role Example

Create and manage IAM Roles:

```python
# Create an IAM Role for Lambda
assume_role_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}

create_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="create_resource",
    arguments={
        "type_name": "AWS::IAM::Role",
        "desired_state": {
            "RoleName": "lambda-execution-role",
            "AssumeRolePolicyDocument": assume_role_policy,
            "Description": "Execution role for Lambda functions",
            "MaxSessionDuration": 3600,
            "Tags": [
                {
                    "Key": "Environment",
                    "Value": "Production"
                }
            ]
        },
        "client_token": "create-role-token"
    }
)

# Update the role description
patch_document = [
    {
        "op": "replace",
        "path": "/Description",
        "value": "Updated execution role for Lambda functions"
    }
]

update_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="update_resource",
    arguments={
        "type_name": "AWS::IAM::Role",
        "identifier": "lambda-execution-role",
        "patch_document": json.dumps(patch_document),
        "client_token": "update-role-token"
    }
)
```

## Handling Asynchronous Operations

Many CloudControl API operations are asynchronous. Here's how to track and wait for operations to complete:

```python
import asyncio
import time

async def wait_for_operation_completion(request_token, timeout=300, interval=5):
    """Wait for a CloudControl API operation to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        status_result = await use_mcp_tool(
            server_name="awslabs.aws-cloudcontrol-mcp-server",
            tool_name="get_resource_request_status",
            arguments={"request_token": request_token}
        )
        
        operation_status = status_result['ProgressEvent'].get('OperationStatus')
        
        if operation_status == 'SUCCESS':
            return status_result
        elif operation_status in ['FAILED', 'CANCELED']:
            return status_result
            
        await asyncio.sleep(interval)
        
    return {'error': f'Operation timed out after {timeout} seconds'}

# Example usage
create_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="create_resource",
    arguments={
        "type_name": "AWS::S3::Bucket",
        "desired_state": {"BucketName": "my-bucket"},
        "client_token": "create-bucket-token"
    }
)

request_token = create_result['ProgressEvent']['RequestToken']
status_result = await wait_for_operation_completion(request_token)

if 'error' in status_result:
    print(f"Operation failed: {status_result['error']}")
else:
    print(f"Operation completed successfully: {status_result['ProgressEvent']['OperationStatus']}")
```

## Idempotency with Client Tokens

Use client tokens to ensure operations are only executed once:

```python
import uuid

# Generate a unique client token
client_token = f"create-resource-{uuid.uuid4()}"

# Even if this operation is called multiple times with the same client_token,
# only one resource will be created
create_result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="create_resource",
    arguments={
        "type_name": "AWS::Logs::LogGroup",
        "desired_state": {
            "LogGroupName": "/aws/lambda/my-function",
            "RetentionInDays": 7
        },
        "client_token": client_token
    }
)
```

## Error Handling

Handle errors from CloudControl API operations:

```python
# Example of error handling
result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="get_resource",
    arguments={
        "type_name": "AWS::S3::Bucket",
        "identifier": "non-existent-bucket"
    }
)

if 'error' in result:
    # Handle the error
    error_message = result['error']
    if "ResourceNotFoundException" in error_message:
        print("The specified resource does not exist")
    elif "AccessDeniedException" in error_message:
        print("You don't have permission to access this resource")
    else:
        print(f"An error occurred: {error_message}")
```

## Resource Type Discovery

Discover available resource types:

```python
# List all available resource types
result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="list_resource_types",
    arguments={}
)

# Filter resource types by prefix
result = await use_mcp_tool(
    server_name="awslabs.aws-cloudcontrol-mcp-server",
    tool_name="list_resource_types",
    arguments={
        "filters": {
            "TypeNamePrefix": "AWS::S3::"
        }
    }
)
```

## AWS CloudControl API Resources

This server uses the AWS CloudControl API for:
- Creating, reading, updating, and deleting AWS resources
- Listing resources of specific types
- Tracking and managing resource operation requests

### Official Documentation

- [AWS CloudControl API User Guide](https://docs.aws.amazon.com/cloudcontrolapi/latest/userguide/what-is-cloudcontrolapi.html)
- [AWS CloudControl API Reference](https://docs.aws.amazon.com/cloudcontrolapi/latest/APIReference/Welcome.html)
- [AWS CloudFormation Resource Types Reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html)

## Security Considerations

- Use AWS profiles for credential management
- Use IAM policies to restrict access to only the required AWS resources
- Use temporary credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN) from AWS STS for enhanced security
- Implement AWS IAM roles with temporary credentials for applications and services
- Regularly rotate credentials and use the shortest practical expiration time for temporary credentials
- Use client tokens for idempotency to prevent duplicate resource creation
