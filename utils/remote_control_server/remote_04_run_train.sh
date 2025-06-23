#!/bin/bash

# ==============================================================================
# Script: remote_04_run_train.sh
# Description: Initiates a model training process on the remote server.
#              It synchronizes the 'main' folder, runs the training script,
#              and then syncs back the training results ('runs' folder)
#              to the local machine.
# ==============================================================================

# --- CONFIGURATION ---
REMOTE_USER="kali"
REMOTE_IP="192.168.1.106"
LOCAL_PROJECT_PATH="/Users/admin/Desktop/Driverlens"
REMOTE_PROJECT_PATH="/home/kali/Desktop/Driverlens"
PYTHON_VERSION="python" # Or python3.10 if specific version is required
TRAIN_SCRIPT_PATH="scripts/3_train_yolo.py" # Path relative to REMOTE_PROJECT_PATH

# --- PROCESS ---
echo "--- REMOTE MODEL TRAINING PROCESS ---"
echo "====================================="

# 1. Synchronize 'main' folder from local to remote
echo "1/3: Synchronizing 'scripts' folder to remote server..."
rsync -avz --delete "$LOCAL_PROJECT_PATH/scripts/" "$REMOTE_USER@$REMOTE_IP:$REMOTE_PROJECT_PATH/scripts/"
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to synchronize 'scripts' folder. Check connection."
    exit 1
fi
echo "✅ 'scripts' folder updated."
echo ""

# 2. Start remote training (activate venv and run script)
echo "2/3: Starting remote training process... (This may take a long time)"
ssh "$REMOTE_USER@$REMOTE_IP" "cd $REMOTE_PROJECT_PATH && source .venv/bin/activate && $PYTHON_VERSION $TRAIN_SCRIPT_PATH"
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Remote training process failed! Check remote libraries and script."
    exit 1
fi
echo "✅ Training completed successfully."
echo ""

# 3. Synchronize results ('runs' folder) back to the local machine
echo "3/3: Synchronizing results ('runs' folder) back to local machine..."
rsync -avz --delete "$REMOTE_USER@$REMOTE_IP:$REMOTE_PROJECT_PATH/runs/" "$LOCAL_PROJECT_PATH/runs/"
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to synchronize results. Check connection."
    exit 1
fi
echo "✅ Results synchronized successfully."
echo ""

echo "🎉 All training processes completed successfully!"