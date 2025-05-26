#!/bin/bash

# Create virtual environment for VisionVend project
echo "Creating virtual environment..."
cd /mnt/c/Users/david/Documents/Artificial-Me-Org/VisionVend
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing server dependencies..."
cd src/server
pip install -r requirements.txt

echo "Installing aiosqlite for SQLite async support..."
pip install aiosqlite

echo "Testing database setup..."
python test_database.py

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To use the virtual environment:"
echo "  cd /mnt/c/Users/david/Documents/Artificial-Me-Org/VisionVend"
echo "  source venv/bin/activate"
echo "  cd src/server"
echo "  python app.py"