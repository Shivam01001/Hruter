#!/bin/bash

# Setup script for Hruter - Smart Brute Force Tool
# For Kali Linux / Debian-based systems

echo "[*] Setting up Hruter..."

# Check if Python3 is installed
if ! command -v python3 &> /dev/null
then
    echo "[-] Python3 could not be found. Please install it."
    exit
fi

# Install requirements
echo "[*] Installing dependencies..."
pip3 install -r requirements.txt

# Make the main script executable
chmod +x hruter.py

# Create a symbolic link if possible
if [ -d "$HOME/.local/bin" ]; then
    ln -sf "$(pwd)/hruter.py" "$HOME/.local/bin/hruter"
    echo "[+] Tool linked to ~/.local/bin/hruter"
    echo "[!] You can now run it by typing 'hruter'"
else
    echo "[!] Add this directory to your PATH or copy hruter.py to /usr/local/bin to run it globally."
fi

echo "[+] Setup complete!"
