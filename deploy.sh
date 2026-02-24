#!/bin/bash
# Deploy Polymarket bot to CloudClaw VPS

set -e

echo "=========================================="
echo "Polymarket Bot - Deployment Script"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Step 1: Checking Python version...${NC}"
python3 --version || { echo -e "${RED}Python 3 not found${NC}"; exit 1; }

echo ""
echo -e "${GREEN}Step 2: Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

echo ""
echo -e "${GREEN}Step 3: Activating virtual environment...${NC}"
source venv/bin/activate

echo ""
echo -e "${GREEN}Step 4: Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo -e "${GREEN}Step 5: Creating directories...${NC}"
mkdir -p logs

echo ""
echo -e "${GREEN}Step 6: Setting up environment...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}✅ Created .env file${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env and add your PRIVATE_KEY${NC}"
else
    echo "✅ .env file already exists"
fi

echo ""
echo -e "${GREEN}Step 7: Making scripts executable...${NC}"
chmod +x emergency_stop.sh
chmod +x deploy.sh
chmod +x bot.py
chmod +x test_connection.py

echo ""
echo -e "${GREEN}Step 8: Testing connection...${NC}"
python3 test_connection.py

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env file:"
echo "   nano .env"
echo ""
echo "2. Test bot in dry-run mode:"
echo "   python3 bot.py"
echo ""
echo "3. Run bot in live mode:"
echo "   python3 bot.py --live"
echo ""
echo "4. Set up as systemd service (24/7 operation):"
echo "   sudo cp systemd/polymarket-bot.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable polymarket-bot"
echo "   sudo systemctl start polymarket-bot"
echo ""
echo "5. Monitor logs:"
echo "   tail -f logs/polymarket_bot.log"
echo ""
