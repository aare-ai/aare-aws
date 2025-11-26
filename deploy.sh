#!/bin/bash

# aare.ai AWS Deployment Script
# Deploy the serverless application to AWS

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
STAGE=${1:-dev}
REGION=${2:-us-east-1}
PROFILE=${3:-default}

echo -e "${GREEN}🚀 Deploying aare.ai to AWS${NC}"
echo -e "Stage: ${YELLOW}$STAGE${NC}"
echo -e "Region: ${YELLOW}$REGION${NC}"
echo -e "Profile: ${YELLOW}$PROFILE${NC}"

# Check prerequisites
echo -e "\n${GREEN}Checking prerequisites...${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}"

# Install dependencies
echo -e "\n${GREEN}Installing dependencies...${NC}"
npm install

# Run tests
echo -e "\n${GREEN}Running tests...${NC}"
python3 -m pytest tests/ -v || {
    echo -e "${RED}❌ Tests failed. Fix issues before deploying.${NC}"
    exit 1
}

# Deploy with Serverless Framework
echo -e "\n${GREEN}Deploying with Serverless Framework...${NC}"
npx serverless deploy \
    --stage $STAGE \
    --region $REGION \
    --aws-profile $PROFILE \
    --verbose

# Get deployment info
echo -e "\n${GREEN}Getting deployment information...${NC}"
npx serverless info \
    --stage $STAGE \
    --region $REGION \
    --aws-profile $PROFILE

# Upload initial ontologies
echo -e "\n${GREEN}Uploading initial ontologies...${NC}"
python3 scripts/upload_ontologies.py \
    --stage $STAGE \
    --region $REGION \
    --profile $PROFILE

echo -e "\n${GREEN}✅ Deployment complete!${NC}"
echo -e "${YELLOW}API endpoint and API key are shown above.${NC}"
echo -e "${YELLOW}Save your API key securely - you won't be able to see it again.${NC}"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "\n${GREEN}Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please update .env with your API endpoint and key.${NC}"
fi

echo -e "\n${GREEN}Next steps:${NC}"
echo -e "1. Save your API key from the output above"
echo -e "2. Update .env with your API endpoint and key"
echo -e "3. Test the API: ${YELLOW}python3 scripts/test_api.py${NC}"
echo -e "4. View CloudWatch logs: ${YELLOW}serverless logs -f verify --tail${NC}"