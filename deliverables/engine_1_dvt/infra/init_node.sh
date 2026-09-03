#!/usr/bin/env bash
# ==============================================================================
# Engine 1 Node Operator Initialization Script
# Stack: Obol Charon DVT + Lighthouse + Nethermind + MEV-Boost
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "======================================================================"
echo "🚀 Initializing Engine 1 DVT Node Operator Infrastructure"
echo "======================================================================"

# 1. Check Docker & Docker Compose
if ! command -v docker &>/dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH."
    exit 1
fi

if ! docker compose version &>/dev/null; then
    echo "❌ Error: docker compose plugin is not available."
    exit 1
fi
echo "✅ Docker environment verified."

# 2. Initialize Environment File (.env)
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️ Please review and edit .env to configure your OPERATOR_PUBLIC_IP and FEE_RECIPIENT_ADDRESS."
else
    echo "✅ .env configuration file already exists."
fi

# 3. Generate Engine API JWT Secret (jwt.hex)
if [ ! -f jwt.hex ]; then
    echo "🔑 Generating 256-bit Engine API JWT secret (jwt.hex)..."
    if command -v openssl &>/dev/null; then
        openssl rand -hex 32 > jwt.hex
    else
        head -c 32 /dev/urandom | xxd -p -c 32 > jwt.hex
    fi
    chmod 600 jwt.hex
    echo "✅ Generated jwt.hex with secure 0600 permissions."
else
    if [ -d jwt.hex ]; then
        echo "❌ Error: jwt.hex exists as a directory! Removing invalid directory..."
        rm -rf jwt.hex
        openssl rand -hex 32 > jwt.hex
        chmod 600 jwt.hex
        echo "✅ Fixed and regenerated jwt.hex as a secure file."
    else
        echo "✅ jwt.hex secret already exists."
    fi
fi

# 4. Prepare Local Data Directories with Proper Permissions
echo "📁 Initializing local data directories..."
mkdir -p .charon/validator_keys
chmod 700 .charon .charon/validator_keys

# 5. Validate Docker Compose Configuration
echo "🔍 Validating docker-compose.yml configuration..."
docker compose config >/dev/null
echo "✅ Docker Compose syntax and volume mapping verified successfully."

echo "======================================================================"
echo "🎉 Initialization Complete!"
echo "Next Steps:"
echo "  1. Run DKG ceremony or place your .charon/cluster-lock.json and validator_keys/ inside .charon/"
echo "  2. Start the staking stack: docker compose up -d"
echo "  3. Monitor logs:            docker compose logs -f charon"
echo "======================================================================"
