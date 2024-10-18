#!/bin/bash
echo "active python environment"
source .venv/bin/activate
echo "start aibox app..."
nohup python app.py >>./run.log 2>&1 &
sleep 5
lsof -i:8886
