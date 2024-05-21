#!/bin/bash
source .venv/bin/activate
nohup python app.py >>./app-run.log 2>&1 &