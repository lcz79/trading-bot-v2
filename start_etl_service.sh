#!/bin/bash
# Script to start the ETL Service (Market Analysis)

echo "Starting ETL Service - Market Analysis..."
echo "This terminal must remain open for the service to run."
echo "Press Ctrl+C to stop the service."
echo ""

python3 etl_service.py
