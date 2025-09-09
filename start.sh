#!/bin/bash

# Simple Amazon Job Poller - Quick Start Script
# This script sets up and starts the job poller service

echo "🚀 Amazon Job Poller - Quick Start"
echo "=================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check if config file exists
if [ ! -f "server_config.json" ]; then
    echo "❌ server_config.json not found!"
    echo "Please update the configuration file with your credentials"
    exit 1
fi

# Install dependencies if requirements.txt exists and not already installed
if [ -f "requirements.txt" ] && [ "${SKIP_DEPS:-}" != "1" ]; then
    echo "📦 Checking dependencies..."
    # Check if key dependencies are available
    if python3 -c "import requests, asyncio" 2>/dev/null; then
        echo "✅ Dependencies already available"
    else
        echo "📦 Installing dependencies..."
        # Use pip from virtual environment if available, otherwise system pip
        if [ -n "$VIRTUAL_ENV" ]; then
            pip install -r requirements.txt
        else
            pip3 install -r requirements.txt --user
        fi
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install dependencies"
            echo "💡 Try activating a virtual environment first: source ../venv/bin/activate"
            echo "💡 Or skip dependency check: SKIP_DEPS=1 ./start.sh start"
            exit 1
        fi
    fi
fi

# Handle command line arguments first
case "${1:-start}" in
    "start")
        # Check if service is already running
        if python3 run_server.py status | grep -q "RUNNING"; then
            echo "⚠️  Service is already running"
            echo "Use './start.sh stop' to stop or './start.sh restart' to restart"
            exit 0
        fi
        echo "🎯 Starting job poller service..."
        python3 run_server.py start
        ;;
    "stop")
        echo "🛑 Stopping job poller service..."
        python3 run_server.py stop
        ;;
    "restart")
        echo "🔄 Restarting job poller service..."
        python3 run_server.py restart
        ;;
    "status")
        python3 run_server.py status
        ;;
    "logs")
        echo "📄 Recent logs:"
        python3 run_server.py logs --lines 30
        ;;
    "success")
        echo "✅ Recent successful bookings:"
        python3 run_server.py logs --type success --lines 10
        ;;
    "errors")
        echo "❌ Recent errors:"
        python3 run_server.py logs --type error --lines 10
        ;;
    "foreground")
        echo "🖥️  Starting in foreground mode (Ctrl+C to stop)..."
        python3 run_server.py start --foreground
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|success|errors|foreground}"
        echo ""
        echo "Commands:"
        echo "  start      - Start the service in background"
        echo "  stop       - Stop the service"
        echo "  restart    - Restart the service"
        echo "  status     - Show service status"
        echo "  logs       - Show recent general logs"
        echo "  success    - Show recent successful bookings"
        echo "  errors     - Show recent errors"
        echo "  foreground - Start in foreground (for testing)"
        exit 1
        ;;
esac
