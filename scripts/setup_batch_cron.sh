#!/bin/bash

################################################################################
# Setup Cron Job for Batch Processing Every 2 Hours
################################################################################

echo "=============================================================================="
echo "              BATCH PROCESSING CRON JOB SETUP"
echo "=============================================================================="
echo ""
echo "This will configure batch processing to run every 2 hours"
echo "Schedule: Every day at 00:00, 02:00, 04:00, 06:00, ..., 22:00"
echo ""

# Get the project directory
PROJECT_DIR="/home/top/bigData/remote-satellite-lambda-pipeline"
CRON_SCRIPT="$PROJECT_DIR/scripts/cron_batch_job.sh"

# Verify the script exists
if [ ! -f "$CRON_SCRIPT" ]; then
    echo "Error: Cron script not found at $CRON_SCRIPT"
    exit 1
fi

# Make sure script is executable
chmod +x "$CRON_SCRIPT"
echo "✓ Cron script is executable"

# Create cron entry
CRON_ENTRY="0 */2 * * * $CRON_SCRIPT"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$CRON_SCRIPT"; then
    echo ""
    echo "⚠ Cron job already exists!"
    echo ""
    echo "Current cron jobs:"
    crontab -l | grep "$CRON_SCRIPT"
    echo ""
    read -p "Do you want to replace it? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
    
    # Remove old entry
    crontab -l | grep -v "$CRON_SCRIPT" | crontab -
    echo "✓ Removed old cron job"
fi

# Add new cron entry
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo ""
echo "✓ Cron job installed successfully!"
echo ""
echo "=============================================================================="
echo "Cron Schedule:"
echo "=============================================================================="
echo "  Expression: 0 */2 * * *"
echo "  Meaning: At minute 0 past every 2nd hour"
echo "  Schedule: 00:00, 02:00, 04:00, 06:00, 08:00, 10:00,"
echo "            12:00, 14:00, 16:00, 18:00, 20:00, 22:00"
echo ""
echo "  Script: $CRON_SCRIPT"
echo "  Logs: $PROJECT_DIR/logs/batch_cron_YYYY-MM-DD_HH-MM-SS.log"
echo ""
echo "=============================================================================="
echo "Verify Installation:"
echo "=============================================================================="
echo "  View cron jobs:  crontab -l"
echo "  Edit cron jobs:  crontab -e"
echo "  Remove cron job: crontab -l | grep -v 'cron_batch_job.sh' | crontab -"
echo ""
echo "  Test manually:   $CRON_SCRIPT"
echo "  View logs:       ls -lth $PROJECT_DIR/logs/batch_cron_*.log"
echo "  Monitor logs:    tail -f $PROJECT_DIR/logs/batch_cron_*.log"
echo ""
echo "=============================================================================="
echo "Current Cron Jobs:"
echo "=============================================================================="
crontab -l
echo ""
echo "✓ Setup complete!"
echo ""
