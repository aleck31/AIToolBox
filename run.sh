#!/bin/bash
echo "active python environment"
source .venv/bin/activate

echo "Start aibox app..."
nohup python app.py >>./logs/run.log 2>&1 &

echo -n "Checking process status"
for i in {1..3}; do
    sleep 1
    echo -n "."
done
echo ""
lsof -i:8886
