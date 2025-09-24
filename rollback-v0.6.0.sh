#!/bin/bash

# Rollback script for v0.6.0 deployment
# This script reverts the fogis-api-client-service to the previous version

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔄 Rolling back fogis-api-client-service from v0.6.0...${NC}"

# Stop current service
echo -e "${YELLOW}⏹️  Stopping current v0.6.0 service...${NC}"
docker-compose stop fogis-api-client-service

# Restore backup configuration
echo -e "${YELLOW}📋 Restoring previous docker-compose configuration...${NC}"
if [ -f "docker-compose.yml.backup-v0.5.5-"* ]; then
    BACKUP_FILE=$(ls docker-compose.yml.backup-v0.5.5-* | head -1)
    cp "$BACKUP_FILE" docker-compose.yml
    echo -e "${GREEN}✅ Restored configuration from $BACKUP_FILE${NC}"
else
    echo -e "${RED}❌ No backup configuration found!${NC}"
    echo -e "${YELLOW}⚠️  Manually updating to previous version...${NC}"
    sed -i 's/image: fogis-api-client-python:0.6.0/image: ghcr.io\/pitchconnect\/fogis-api-client-python:0.5.5/' docker-compose.yml
fi

# Start service with previous version
echo -e "${YELLOW}🚀 Starting service with previous version...${NC}"
docker-compose up -d fogis-api-client-service

# Wait for service to start
echo -e "${YELLOW}⏳ Waiting for service to start...${NC}"
sleep 15

# Check health
echo -e "${YELLOW}🔍 Checking service health...${NC}"
if curl -s http://localhost:9086/health > /dev/null; then
    echo -e "${GREEN}✅ Rollback completed successfully!${NC}"
    echo -e "${GREEN}✅ Service is healthy and responding${NC}"
else
    echo -e "${RED}❌ Rollback failed - service is not responding${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Rollback to previous version completed successfully!${NC}"
