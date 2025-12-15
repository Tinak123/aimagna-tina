#!/bin/bash

# Start backend in background
echo "Starting backend..."
./start_backend.sh > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
echo "Waiting for backend to start..."
sleep 5

# Start frontend
echo "Starting frontend..."
./start_frontend.sh

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
