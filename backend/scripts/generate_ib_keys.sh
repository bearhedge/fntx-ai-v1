#!/bin/bash
#
# Generate IB REST API OAuth Keys
# Creates RSA key pairs and Diffie-Hellman parameters for IBKR authentication
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paths
PROJECT_ROOT="/home/info/fntx-ai-v1"
KEYS_DIR="${PROJECT_ROOT}/config/keys"

echo -e "${GREEN}IB REST API Key Generation Script${NC}"
echo "=================================="
echo

# Create keys directory if it doesn't exist
if [ ! -d "${KEYS_DIR}" ]; then
    echo -e "${YELLOW}Creating keys directory...${NC}"
    mkdir -p "${KEYS_DIR}"
    echo -e "${GREEN}✓ Created ${KEYS_DIR}${NC}"
fi

# Check if keys already exist
if [ -f "${KEYS_DIR}/private_signature.pem" ] || [ -f "${KEYS_DIR}/private_encryption.pem" ]; then
    echo -e "${YELLOW}⚠️  Warning: Keys already exist!${NC}"
    read -p "Do you want to overwrite existing keys? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborted. Existing keys preserved.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Generating RSA Keys...${NC}"
echo

# Generate signing keys
echo "1. Generating signing key pair..."
openssl genrsa -out "${KEYS_DIR}/private_signature.pem" 2048 2>/dev/null
openssl rsa -in "${KEYS_DIR}/private_signature.pem" -outform PEM -pubout -out "${KEYS_DIR}/public_signature.pem" 2>/dev/null
echo -e "${GREEN}✓ Generated signing keys${NC}"

# Generate encryption keys
echo "2. Generating encryption key pair..."
openssl genrsa -out "${KEYS_DIR}/private_encryption.pem" 2048 2>/dev/null
openssl rsa -in "${KEYS_DIR}/private_encryption.pem" -outform PEM -pubout -out "${KEYS_DIR}/public_encryption.pem" 2>/dev/null
echo -e "${GREEN}✓ Generated encryption keys${NC}"

# Generate Diffie-Hellman parameters
echo "3. Generating Diffie-Hellman parameters (this may take a moment)..."
openssl dhparam -outform PEM 2048 -out "${KEYS_DIR}/dhparam.pem" 2>/dev/null
echo -e "${GREEN}✓ Generated DH parameters${NC}"

# Set proper permissions
echo
echo -e "${GREEN}Setting file permissions...${NC}"
chmod 600 "${KEYS_DIR}/private_"*.pem
chmod 644 "${KEYS_DIR}/public_"*.pem
chmod 644 "${KEYS_DIR}/dhparam.pem"
echo -e "${GREEN}✓ Permissions set${NC}"

# Display results
echo
echo -e "${GREEN}Key Generation Complete!${NC}"
echo "======================="
echo
echo "Generated files:"
ls -la "${KEYS_DIR}/"*.pem | awk '{print "  " $9 " (" $1 ")"}'

echo
echo -e "${YELLOW}IMPORTANT: Submit these files to IBKR:${NC}"
echo "  1. ${KEYS_DIR}/public_signature.pem"
echo "  2. ${KEYS_DIR}/public_encryption.pem"
echo "  3. ${KEYS_DIR}/dhparam.pem"

echo
echo -e "${RED}SECURITY WARNING:${NC}"
echo "  - NEVER share or commit the private_*.pem files"
echo "  - Add config/keys/ to your .gitignore"
echo "  - Back up these keys securely"

# Check .gitignore
echo
if grep -q "config/keys/" "${PROJECT_ROOT}/.gitignore" 2>/dev/null; then
    echo -e "${GREEN}✓ config/keys/ is already in .gitignore${NC}"
else
    echo -e "${YELLOW}Adding config/keys/ to .gitignore...${NC}"
    echo -e "\n# IB API Keys (NEVER COMMIT)\nconfig/keys/" >> "${PROJECT_ROOT}/.gitignore"
    echo -e "${GREEN}✓ Updated .gitignore${NC}"
fi

# Create example .env if it doesn't exist
ENV_FILE="${PROJECT_ROOT}/config/.env"
if [ ! -f "${ENV_FILE}" ]; then
    echo
    echo -e "${YELLOW}Creating example .env file...${NC}"
    cat > "${ENV_FILE}.example" << EOF
# IB REST API Configuration
IB_CONSUMER_KEY=your_consumer_key_here
IB_ACCESS_TOKEN_SECRET="your_encrypted_token_secret_here"
IB_SIGNATURE_KEY_PATH=${KEYS_DIR}/private_signature.pem
IB_ENCRYPTION_KEY_PATH=${KEYS_DIR}/private_encryption.pem
IB_DH_PARAM_PATH=${KEYS_DIR}/dhparam.pem
IB_REALM=limited_poa
IB_IS_LIVE=true

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=options_data
DB_USER=postgres
DB_PASSWORD=theta_data_2024
EOF
    echo -e "${GREEN}✓ Created ${ENV_FILE}.example${NC}"
    echo -e "${YELLOW}Copy this to ${ENV_FILE} and add your credentials${NC}"
fi

echo
echo -e "${GREEN}Setup complete! Next steps:${NC}"
echo "  1. Submit the public keys to IBKR"
echo "  2. Update ${ENV_FILE} with your consumer key and token"
echo "  3. Run: python backend/core/test_ib_rest_auth.py"