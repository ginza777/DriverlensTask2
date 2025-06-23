#!/bin/bash

# ==============================================================================
# Script: remote_06_sync_any_folder.sh
# Description: Performs a bidirectional synchronization for a specified
#              folder or file between the local machine and the remote server.
#              This means changes made on either side will be propagated to the other.
# Usage: ./remote_06_sync_any_folder.sh <folder_or_file_name>
# Example: ./remote_06_sync_any_folder.sh "my_custom_scripts"
#          ./remote_06_sync_any_folder.sh "config.ini"
# ==============================================================================

# --- CONFIGURATION ---
REMOTE_USER="kali"
REMOTE_IP="192.168.1.106"
LOCAL_PROJECT_PATH="/Users/admin/Desktop/Driverlens"
REMOTE_PROJECT_PATH="/home/kali/Desktop/Driverlens"

# --- SCRIPT LOGIC ---

# 1. Argument check
if [ -z "$1" ]; then
    echo "❌ ERROR: You must specify a folder or file name to synchronize."
    echo "Usage: $0 <folder_or_file_name>"
    exit 1
fi

TARGET_ITEM="$1"

# 2. Construct full paths
LOCAL_SOURCE_TARGET_PATH="$LOCAL_PROJECT_PATH/$TARGET_ITEM"
REMOTE_DEST_TARGET_PATH="$REMOTE_PROJECT_PATH/$TARGET_ITEM"

# 3. Determine if it's a directory to append '/' for rsync
# This ensures that if it's a directory, rsync syncs its *contents*
if [ -d "$LOCAL_SOURCE_TARGET_PATH" ]; then
    LOCAL_SOURCE_TARGET_PATH="$LOCAL_SOURCE_TARGET_PATH/"
    REMOTE_DEST_TARGET_PATH="$REMOTE_DEST_TARGET_PATH/"
    echo "Synchronizing directory: $TARGET_ITEM"
elif [ -f "$LOCAL_SOURCE_TARGET_PATH" ]; then
    echo "Synchronizing file: $TARGET_ITEM"
else
    echo "❌ ERROR: Local source '$LOCAL_SOURCE_TARGET_PATH' does not exist or is not a regular file/directory."
    exit 1
fi

# 4. Bidirectional synchronization
echo "--- BIDIRECTIONAL SYNCHRONIZATION OF '$TARGET_ITEM' ---"
echo "========================================================"

echo "🔄 Step 1/2: Sending changes from local to remote..."
# -a: archive mode (preserves permissions, timestamps, etc.)
# -v: verbose
# -z: compress file data during transfer
# -u: update (skip files that are newer on the destination)
# --delete: delete extraneous files from destination dirs (if target is a folder with trailing slash)
#           Careful with --delete in bidirectional syncs, it can lead to data loss if not understood.
#           For a general 'sync any folder' where user expects full sync, it's often desired.
rsync -avzu --delete "$LOCAL_SOURCE_TARGET_PATH" "$REMOTE_USER@$REMOTE_IP:$REMOTE_DEST_TARGET_PATH"
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Problem synchronizing from local to remote."
    exit 1
fi
echo "✅ Local to remote sync complete."
echo ""

echo "🔄 Step 2/2: Receiving changes from remote to local..."
rsync -avzu --delete "$REMOTE_USER@$REMOTE_IP:$REMOTE_DEST_TARGET_PATH" "$LOCAL_SOURCE_TARGET_PATH"
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Problem synchronizing from remote to local."
    exit 1
fi
echo "✅ Remote to local sync complete."
echo ""

echo "🎉 Synchronization successful for '$TARGET_ITEM'!"