#!/bin/bash
source .venv/bin/activate
nohup python app.py >>./run.log 2>&1 &