#!/bin/bash

# Claude Code MCP Server Setup Script
# This script initializes MCP servers for new Claude Code projects

echo "Setting up Claude Code MCP servers..."

# Add Context7 MCP server
echo "Adding Context7 MCP server..."
claude mcp add --transport http context7 https://mcp.context7.com/mcp --header "CONTEXT7_API_KEY: ctx7sk-30d98671-d928-4a4c-b885-439411c9f81e"

echo "MCP servers setup complete!"