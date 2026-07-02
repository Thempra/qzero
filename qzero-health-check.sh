#!/bin/bash

# QZero Health Check - Cron task for autonomous maintenance
# Good for: Me (developer awareness)
# Run: Hourly cron

PROJECT_DIR="/home/thempra/projects/qzero"
LOG_FILE="$PROJECT_DIR/health-check.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] QZero Health Check started" | tee -a "$LOG_FILE"

cd "$PROJECT_DIR" || exit 1

# 1. Check git status
echo "[$TIMESTAMP] Git status:" | tee -a "$LOG_FILE"
git status --porcelain 2>&1 | tee -a "$LOG_FILE"
echo "---" | tee -a "$LOG_FILE"

# 2. Check recent commits
echo "[$TIMESTAMP] Recent commits:" | tee -a "$LOG_FILE"
git log -3 --oneline 2>&1 | tee -a "$LOG_FILE"
echo "---" | tee -a "$LOG_FILE"

# 3. Check project size
SIZE=$(du -sh . 2>/dev/null | cut -f1)
echo "[$TIMESTAMP] Project size: $SIZE" | tee -a "$LOG_FILE"
echo "---" | tee -a "$LOG_FILE"

# 4. Check for large files > 10MB
echo "[$TIMESTAMP] Large files (>10MB):" | tee -a "$LOG_FILE"
find . -type f -size +10M -exec du -h {} \; 2>/dev/null | sort -rh | head -10 | tee -a "$LOG_FILE"
echo "---" | tee -a "$LOG_FILE"

# 5. Check for markdown files that need attention
echo "[$TIMESTAMP] Modified markdown files:" | tee -a "$LOG_FILE"
git diff --name-only --diff-filter=M '*.md' 2>/dev/null | tee -a "$LOG_FILE"
echo "---" | tee -a "$LOG_FILE"

echo "[$TIMESTAMP] QZero Health Check completed" | tee -a "$LOG_FILE"