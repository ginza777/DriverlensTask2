#!/bin/bash

# ==============================================================================
# Script: remote_05_sync_data_to_local.sh
# Description: Safely synchronizes specific data folders and configuration files
#              from the remote server to the local machine.
#              - It ADDS NEW files from remote to local for specified data folders.
#              - It UPDATES 'data.yaml' on the local machine with the remote version.
#              - IMPORTANT: NO FILES ARE DELETED ON THE LOCAL MACHINE by this script.
# ==============================================================================

# --- CONFIGURATION ---
REMOTE_USER="kali"
REMOTE_IP="192.168.1.106"
LOCAL_PROJECT_PATH="/Users/admin/Desktop/Driverlens"
REMOTE_PROJECT_PATH="/home/kali/Desktop/Driverlens"

# --- AUTOMATIC SYNCHRONIZATION PROCESS ---
echo "--- SAFE DATA SYNCHRONIZATION FROM REMOTE TO LOCAL ---"
echo "======================================================"
echo ""

# List of folders to safely merge (only new files are added to local)
FOLDERS_TO_MERGE=(
    "data/dataset"
    "data/annotations"
    "runs"
)

# List of individual files to always update (remote version overwrites local)
FILES_TO_UPDATE=(
    "data.yaml"
)

# Safely synchronize folders (only add new files, do not overwrite existing, do not delete)
for FOLDER in "${FOLDERS_TO_MERGE[@]}"; do
    echo "🔄 Synchronizing new files in '$FOLDER' folder..."
    SOURCE_PATH="$REMOTE_PROJECT_PATH/$FOLDER/"
    DEST_PATH="$LOCAL_PROJECT_PATH/$FOLDER/"

    # --ignore-existing: skip updating files that exist on the receiver (local)
    # --exclude='.*': Exclude hidden files like .DS_Store
    rsync -avz --ignore-existing --exclude='.*' "$REMOTE_USER@$REMOTE_IP:$SOURCE_PATH" "$DEST_PATH"

    if [ $? -ne 0 ]; then
        echo "❌ ERROR: Failed to synchronize '$FOLDER' folder!"
        exit 1
    fi
    echo "✅ New files in '$FOLDER' folder added."
    echo ""
done

# Force update specific files (remote version replaces local)
for FILE in "${FILES_TO_UPDATE[@]}"; do
    echo "🔄 Force updating '$FILE' file..."
    SOURCE_PATH="$REMOTE_PROJECT_PATH/$FILE"
    DEST_PATH="$LOCAL_PROJECT_PATH/$FILE"

    # This command will always replace the local file with the remote version.
    rsync -avz "$REMOTE_USER@$REMOTE_IP:$SOURCE_PATH" "$DEST_PATH"

     if [ $? -ne 0 ]; then
        echo "❌ ERROR: Failed to update '$FILE' file!"
        exit 1
    fi
    echo "✅ '$FILE' successfully updated."
    echo ""
done

echo "🎉 All synchronization processes completed successfully!"