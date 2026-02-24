#!/bin/bash
# Emergency stop script for Polymarket bot

echo "=========================================="
echo "Emergency Stop - Polymarket Bot"
echo "=========================================="
echo ""

# Find and kill bot processes
BOT_PIDS=$(ps aux | grep "python.*bot.py" | grep -v grep | awk '{print $2}')

if [ -z "$BOT_PIDS" ]; then
    echo "No bot processes found running"
else
    echo "Found bot process(es): $BOT_PIDS"
    echo "Killing..."
    kill -9 $BOT_PIDS
    echo "✅ Bot stopped"
fi

echo ""
echo "If bot was running as systemd service:"
echo "  sudo systemctl stop polymarket-bot"
echo ""
