#!/bin/bash
source venv/bin/activate
export $(grep -v '^#' .env | xargs)
uvicorn src.nl_agent.main:app --reload --host 0.0.0.0 --port 8000
