#!/bin/bash

echo "🏠 Setting up Vikunja for Family Task Management"
echo "================================================"

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p ~/vikunja/{config,db,files}

# Generate a secure JWT secret
echo "🔐 Generating secure JWT secret..."
JWT_SECRET=$(openssl rand -base64 32)

# Copy configuration file
echo "📋 Setting up configuration..."
cp vikunja-config.yml ~/vikunja/config/config.yml

# Replace JWT secret in config
sed -i.bak "s/your-jwt-secret-change-this-to-something-secure/$JWT_SECRET/g" ~/vikunja/config/config.yml

# Update docker-compose with the JWT secret
sed -i.bak "s/your-jwt-secret-change-this-to-something-secure/$JWT_SECRET/g" vikunja-docker-compose.yml

echo "✅ Configuration files created with secure JWT secret"

# Set proper permissions
echo "🔒 Setting proper permissions..."
chmod 755 ~/vikunja
chmod 755 ~/vikunja/config
chmod 755 ~/vikunja/db
chmod 755 ~/vikunja/files

echo ""
echo "🚀 Ready to start Vikunja!"
echo ""
echo "Next steps:"
echo "1. Run: docker-compose -f vikunja-docker-compose.yml up -d"
echo "2. Wait for the service to start (about 30-60 seconds)"
echo "3. Open http://localhost:3456 in your browser"
echo "4. Create the admin account (bartek)"
echo "5. Create user accounts for family members (juno, julius)"
echo "6. Set up the 'Household Chores' shared list"
echo ""
echo "📍 Data will be stored in: ~/vikunja/"
echo "🌐 Access URL: http://localhost:3456"
echo "🔧 For external access, you can later set up a Cloudflare tunnel"
echo ""
echo "Generated JWT Secret: $JWT_SECRET"
echo "(This has been automatically applied to your configuration)"
