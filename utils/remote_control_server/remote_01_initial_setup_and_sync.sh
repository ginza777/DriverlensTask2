#!/bin/bash

# ==============================================================================
# Script: remote_01_initial_setup_and_sync.sh
# Description: Initializes the remote project directory, sets up a Python
#              virtual environment, and performs an initial sync of core
#              project files from the local machine to the remote server.
#              This script is intended to be run once for initial setup.
# ==============================================================================

# --- CONFIGURATION ---
# User for SSH connection on the remote server
REMOTE_USER="kali"
# IP address or hostname of the remote server
REMOTE_IP="192.168.1.106"
# Path to the project root on the LOCAL machine
LOCAL_PROJECT_PATH="/Users/admin/Desktop/Driverlens"
# Path to the project root on the REMOTE server
REMOTE_PROJECT_PATH="/home/kali/Desktop/Driverlens"
# Name of the Python virtual environment
VENV_NAME=".venv"

# --- PROCESS ---
echo "--- REMOTE PROJECT INITIAL SETUP AND SYNCHRONIZATION ---"
echo "========================================================"

# 1. Create project directory and set up virtual environment on the remote server
echo "1/3: Setting up remote project directory and virtual environment..."
ssh "$REMOTE_USER@$REMOTE_IP" << EOF
    mkdir -p "$REMOTE_PROJECT_PATH"
    cd "$REMOTE_PROJECT_PATH"

    if [ ! -d "$VENV_NAME" ]; then
        echo "Creating virtual environment '$VENV_NAME'..."
        python3.10 -m venv "$VENV_NAME"
        echo "Virtual environment created."
    else
        echo "Virtual environment '$VENV_NAME' already exists. Skipping creation."
    fi

    # Activate venv and install basic requirements (optional, if you have a requirements.txt)
    # source "$VENV_NAME/bin/activate"
    # pip install --upgrade pip
    # if [ -f "requirements.txt" ]; then
    #     echo "Installing Python dependencies from requirements.txt..."
    #     pip install -r requirements.txt
    # else
    #     echo "No requirements.txt found in remote project root. Skipping pip install."
    # fi
    # deactivate # Deactivate after initial setup

    echo "Remote setup complete."
EOF

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Remote setup failed. Check SSH connection and permissions."
    exit 1
fi
echo "✅ Remote project directory and virtual environment set up."
echo ""

# 2. Synchronize essential local project files to the remote server
echo "2/3: Synchronizing initial project files from local to remote..."
# Example: sync only specific folders needed for initial setup/training
# Adjust these paths based on your project structure.
# We'll sync 'util' and 'main' as examples.
rsync -avz --delete "$LOCAL_PROJECT_PATH/util/" "$REMOTE_USER@$REMOTE_IP:$REMOTE_PROJECT_PATH/util/"
rsync -avz --delete "$LOCAL_PROJECT_PATH/scripts/" "$REMOTE_USER@$REMOTE_IP:$REMOTE_PROJECT_PATH/scripts/"
# If you have a requirements.txt in your root, sync it as well
rsync -avz "$LOCAL_PROJECT_PATH/requirements.txt" "$REMOTE_USER@$REMOTE_IP:$REMOTE_PROJECT_PATH/"

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Initial file synchronization failed."
    exit 1
fi
echo "✅ Essential project files synchronized."
echo ""

echo "🎉 Initial remote setup and sync completed!"
echo "You can now run other scripts like remote_02_run_download.sh or remote_04_run_train.sh."