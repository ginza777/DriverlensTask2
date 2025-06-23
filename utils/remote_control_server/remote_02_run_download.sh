#!/bin/bash

# ==============================================================================
# Script: remote_02_run_download.sh
# Description: Initiates a dataset download process from Roboflow on the remote server.
#              This script synchronizes the 'util' folder to ensure the latest
#              download script is used, then executes it on the remote machine.
# ==============================================================================

# --- CONFIGURATION ---
REMOTE_USER="kali"
REMOTE_IP="192.168.1.106"
LOCAL_PROJECT_PATH="/Users/admin/Desktop/Driverlens"
REMOTE_PROJECT_PATH="/home/kali/Desktop/Driverlens"
PYTHON_VERSION="python3.10" # Specify the Python version on the remote server
UTIL_SCRIPT_PATH="util/download_dataset_and_extract.py" # Path relative to REMOTE_PROJECT_PATH

# --- PROCESS ---
echo "--- REMOTE DATASET DOWNLOAD PROCESS ---"
echo "======================================="

# 1. Synchronize 'util' folder to the remote server (in case of local changes)
echo "1/2: Synchronizing 'util' folder to remote server..."
rsync -avz --delete "$LOCAL_PROJECT_PATH/util/" "$REMOTE_USER@$REMOTE_IP:$REMOTE_PROJECT_PATH/util/"
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to synchronize 'util' folder. Check connection."
    exit 1
fi
echo "✅ 'util' folder updated."
echo ""

# 2. Execute the download script on the remote server
echo "2/2: Launching '$UTIL_SCRIPT_PATH' on the remote server..."
# Using -t for pseudo-terminal allocation to allow interactive input if the Python script requires it.
# The previous version did not use -t for download, which implies download_dataset_and_extract.py
# might not need interactive input or was refactored to not need it.
# If your Python download script asks for input, uncomment -t.
ssh "$REMOTE_USER@$REMOTE_IP" "cd $REMOTE_PROJECT_PATH && source .venv/bin/activate && $PYTHON_VERSION $UTIL_SCRIPT_PATH"

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Dataset download failed on the remote server! Check the remote script and logs."
    exit 1
fi
echo "✅ Dataset download process completed on remote server."
echo ""

echo "🎉 Remote dataset download workflow finished."