#!/bin/bash
# Script to start localtunnel for the Coding Agents API
# This creates a secure HTTPS tunnel to your local server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}  Coding Agents - Tunnel Setup   ${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

# Check if localtunnel is installed
if ! command -v lt &> /dev/null; then
    echo -e "${YELLOW}⚠ localtunnel not found!${NC}"
    echo ""
    echo "Installing localtunnel via npm..."
    if command -v npm &> /dev/null; then
        npm install -g localtunnel
        echo -e "${GREEN}✓ localtunnel installed successfully!${NC}"
    else
        echo -e "${RED}✗ npm not found. Please install Node.js first:${NC}"
        echo "  Ubuntu/Debian: sudo apt install nodejs npm"
        echo "  MacOS: brew install node"
        exit 1
    fi
fi

# Check if API is running
echo -e "${YELLOW}Checking if API is running...${NC}"
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}✗ API is not running on localhost:8000${NC}"
    echo ""
    echo "Start the API first:"
    echo "  docker-compose up -d"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ API is running!${NC}"
echo ""

# Start localtunnel
echo -e "${BLUE}Starting localtunnel...${NC}"
echo ""

# Start tunnel with local subdomain (optional)
lt --port 8000 --subdomain coding-agent 2>/dev/null || lt --port 8000
