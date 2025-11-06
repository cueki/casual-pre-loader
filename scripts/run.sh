#!/bin/bash

set -e
# two dirs up
cd "$(dirname "$(dirname "${BASH_SOURCE[0]}")")"

echo "hi :3"
echo

# check for python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    echo "Please install Python 3 using your package manager:"
    echo "  Debian/Ubuntu: sudo apt install python3 python3-pip python3-venv"
    echo "  Arch: sudo pacman -S python python-pip"
    echo "  Fedora: sudo dnf install python3 python3-pip python3-virtualenv"
    exit 1
fi

# check for pip
if ! python3 -m pip --version &> /dev/null; then
    echo "Error: pip is not installed."
    echo "Please install it using your package manager:"
    echo "  Debian/Ubuntu: sudo apt install python3-pip"
    echo "  Arch: sudo pacman -S python-pip"
    echo "  Fedora: sudo dnf install python3-pip"
    exit 1
fi

# check for wine
if ! command -v wine &> /dev/null; then
    echo "Warning: Wine is not installed."
    echo "Wine is required to run studiomdl.exe for model precaching."
    echo "Please install it:"
    echo "  Debian/Ubuntu: sudo apt install wine"
    echo "  Arch: sudo pacman -S wine"
    echo "  Fedora: sudo dnf install wine"
    echo
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# check and make .venv
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."

    if ! python3 -m venv --help &> /dev/null; then
        echo "Error: Python venv module is not installed."
        echo "Please install it using your package manager:"
        echo "  Debian/Ubuntu: sudo apt install python3-venv"
        echo "  Arch: python3-venv is included with python"
        echo "  Fedora: sudo dnf install python3-virtualenv"
        exit 1
    fi

    python3 -m venv .venv
    echo
fi

source .venv/bin/activate

if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -q -r requirements.txt
fi

echo "Starting Casual Preloader..."
python3 main.py
