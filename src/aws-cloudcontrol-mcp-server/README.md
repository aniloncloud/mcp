# AWS CloudControl MCP Server

Model Context Protocol (MCP) server for AWS CloudControl API

This MCP server provides tools to access AWS CloudControl API capabilities, focusing on standardized resource management across AWS services.

## Features

- **Create Resources**: Create AWS resources using standardized resource type schemas
- **Read Resources**: Get details about specific AWS resources
- **Update Resources**: Update existing AWS resources using JSON patch documents
- **Delete Resources**: Delete AWS resources
- **List Resources**: Discover resources of a specific type in your AWS account
- **Track Operations**: Monitor the status of asynchronous resource operations
- **Cancel Operations**: Cancel in-progress resource operations
- **List Requests**: List active resource operation requests

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

## AWS CloudControl API Resources

This server uses the AWS CloudControl API for:
- Creating, reading, updating, and deleting AWS resources
- Listing resources of specific types
- Tracking and managing resource operation requests

## Security Considerations

- Use AWS profiles for credential management
- Use IAM policies to restrict access to only the required AWS resources
- Use temporary credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN) from AWS STS for enhanced security
- Implement AWS IAM roles with temporary credentials for applications and services
- Regularly rotate credentials and use the shortest practical expiration time for temporary credentials
