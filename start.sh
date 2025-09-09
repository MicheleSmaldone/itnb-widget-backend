#!/bin/bash
export PYTHONPATH=/app:$PYTHONPATH
cd /app
python -m uvicorn src.snl_poc.api:app --host 0.0.0.0 --port $PORT
s 