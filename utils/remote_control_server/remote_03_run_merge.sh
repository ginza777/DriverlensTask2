#!/bin/bash

# ==============================================================================
# Script: remote_03_run_merge.sh
# Description: Initiates an interactive dataset merging and tuning process
#              on the remote server. It synchronizes the 'util' folder,
#              then runs the merge script, and finally syncs back the
#              modified 'data' folder and 'data.yaml' to the local machine.
# ==============================================================================

# --- CONFIGURATION ---
REMOTE_USER="kali"
REMOTE_IP="192.168.1.106"
LOCAL_PROJECT_PATH="/Users/admin/Desktop/Driverlens"
REMOTE_PROJECT_PATH="/home/kali/Desktop/Driverlens"
PYTHON_VERSION="python3.10" # Specify the Python version on the remote server
UTIL_SCRIPT_PATH="util/merge_dataset_tuning.py" # Path relative to REMOTE_PROJECT_PATH

# --- PROCESS ---
echo "--- REMOTE INTERACTIVE DATASET MERGE & TUNE PROCESS ---"
echo "======================================================="

# 1. Synchronize 'util' folder to the remote server (in case of local changes)
echo "1/3: Synchronizing 'util' folder to remote server..."
rsync -avz --delete "$LOCAL_PROJECT_PATH/util/" "$REMOTE_USER@$REMOTE_IP:$REMOTE_PROJECT_PATH/util/"
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to synchronize 'util' folder. Check connection."
    exit 1
fi
echo "✅ 'util' folder updated."
echo ""

# 2. Execute the merge script in interactive mode on the remote server
echo "2/3: Launching '$UTIL_SCRIPT_PATH' on the remote server..."
echo "ATTENTION! You will now be prompted for input in the remote terminal."

# The -t flag is crucial for enabling interactive prompts from the Python script.
ssh -t "$REMOTE_USER@$REMOTE_IP" "cd $REMOTE_PROJECT_PATH && source .venv/bin/activate && $PYTHON_VERSION $UTIL_SCRIPT_PATH"

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Merge process failed on the remote server! Check the remote script and logs."
    exit 1
fi
echo "✅ Interactive process completed."
echo ""

# 3. Synchronize modified results (data folder and data.yaml) back to the local machine
echo "3/3: Synchronizing modified 'data' folder and 'data.yaml' from remote to local..."
# Use --delete to ensure local matches remote for these critical folders/files
rsync -avz --delete "$REMOTE_USER@$REMOTE_IP:$REMOTE_PROJECT_PATH/data/" "$LOCAL_PROJECT_PATH/data/"
rsync -avz "$REMOTE_USER@$REMOTE_IP:$REMOTE_PROJECT_PATH/data.yaml" "$LOCAL_PROJECT_PATH/data.yaml"

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to synchronize results from remote. Check connection."
    exit 1
fi
echo "✅ Data synchronized successfully."
echo ""

echo "🎉 Remote dataset merge and tune workflow finished."