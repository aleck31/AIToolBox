#!/bin/bash

# Function: Display usage information
show_usage() {
    echo "Usage: $0 {start|stop|restart|status}"
    echo "Commands:"
    echo "  start   - Start the application"
    echo "  stop    - Stop the application"
    echo "  restart - Restart the application"
    echo "  status  - Show application status"
}

# Function: Start the application
start_app() {
    echo "Activating python environment..."
    source .venv/bin/activate

    # Create logs directory if it doesn't exist
    mkdir -p logs

    # Check if process is already running
    if [ -f .pid ]; then
        OLD_PID=$(cat .pid)
        if ps -p $OLD_PID > /dev/null; then
            echo "Application is already running with PID: $OLD_PID"
            return 1
        else
            rm .pid
        fi
    fi

    echo "Starting aibox app..."
    # Use nohup to run in background, use application logger
    nohup python app.py >/dev/null 2>&1 &

    # Save PID
    echo $! > .pid
    PID=$(cat .pid)

    echo -n "Checking process status"
    for i in {1..3}; do
        sleep 1
        echo -n "."
    done
    echo ""

    # Verify process is running
    if ps -p $PID > /dev/null; then
        echo "Application started successfully with PID: $PID"
        echo "To check logs:"
        echo "- Application logs: tail -f logs/app.log"
        echo "- Debug logs: tail -f logs/debug.log"
        echo "To check status: $0 status"
        return 0
    else
        echo "Failed to start application"
        rm .pid
        return 1
    fi
}

# Function: Stop the application
stop_app() {
    if [ -f .pid ]; then
        PID=$(cat .pid)
        if ps -p $PID > /dev/null; then
            echo "Stopping application (PID: $PID)..."
            kill $PID
            sleep 2
            if ps -p $PID > /dev/null; then
                echo "Process still running, forcing stop..."
                kill -9 $PID
            fi
            rm .pid
            echo "Application stopped"
            return 0
        else
            echo "Process is not running"
            rm .pid
            return 1
        fi
    else
        echo "No PID file found"
        return 1
    fi
}

# Function: Check application status
check_status() {
    if [ -f .pid ]; then
        PID=$(cat .pid)
        if ps -p $PID > /dev/null; then
            echo "Application is running with PID: $PID"
            echo "To check logs:"
            echo "- Application logs: tail -f logs/app.log"
            echo "- Debug logs: tail -f logs/debug.log"
            echo "Server listening status:"
            ss -tlnp | grep :8080
            if [ $? -ne 0 ]; then
                echo "Warning: Server process is running but not listening on port 8080"
            fi
            return 0
        else
            echo "Process is not running (stale PID file)"
            rm .pid
            return 1
        fi
    else
        echo "Application is not running"
        return 1
    fi
}

# Main logic
case "$1" in
    start)
        start_app
        ;;
    stop)
        stop_app
        ;;
    restart)
        stop_app
        sleep 2
        start_app
        ;;
    status)
        check_status
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
