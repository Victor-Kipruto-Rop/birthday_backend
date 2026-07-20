#!/bin/bash
set -e

echo "=== Installing Python Dependencies ==="
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "=== Verifying psycopg2 Installation ==="
python -c "import psycopg2; print(f'✅ psycopg2 version: {psycopg2.__version__}')"

echo "=== Installation Complete ==="
ls -la
