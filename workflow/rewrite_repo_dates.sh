#!/bin/bash

# Usage:
#   ./rewrite_repo_dates.sh           → rewrite entire history
#   ./rewrite_repo_dates.sh "2024-01-01" → rewrite commits since that date
#
# WARNING: This script rewrites Git history. Make sure you:
#   1. Have a backup of your repository
#   2. Are working on a local copy (not directly on main/master)
#   3. Understand that this changes commit hashes
#   4. Will need to force-push if updating remote (dangerous!)

set -euo pipefail

# Safety checks
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a Git repository"
    exit 1
fi

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "Warning: You have uncommitted changes."
    echo "Please commit or stash them before running this script."
    exit 1
fi

# Detect current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
IS_MAIN_BRANCH=false
BACKUP_BRANCH=""  # Initialize backup branch variable

if [[ "$CURRENT_BRANCH" == "main" ]] || [[ "$CURRENT_BRANCH" == "master" ]]; then
    IS_MAIN_BRANCH=true
fi

# Warn user about the destructive nature
echo "⚠️  WARNING: This script will rewrite Git history!"
echo ""

if [ "$IS_MAIN_BRANCH" = true ]; then
    echo "🚨 EXTREME CAUTION: You are on branch '$CURRENT_BRANCH'!"
    echo ""
    echo "This is a MAIN/MASTER branch. Rewriting history here is VERY DANGEROUS!"
    echo ""
    echo "Risks:"
    echo "  - All commit hashes will change"
    echo "  - Anyone who cloned this repo will have conflicts"
    echo "  - You MUST force-push to update remote (breaks other people's clones)"
    echo "  - Team members will need to re-clone or reset their local repos"
    echo ""
    echo "⚠️  BACKUP WILL BE CREATED AUTOMATICALLY (mandatory on main/master)"
    echo ""
    read -p "Type 'YES I UNDERSTAND THE RISKS' to continue: " -r
    if [[ ! $REPLY == "YES I UNDERSTAND THE RISKS" ]]; then
        echo "Aborted. Safety first!"
        exit 0
    fi
    echo ""
else
    echo "Current branch: $CURRENT_BRANCH"
    echo ""
    echo "This will:"
    echo "  - Change commit dates and times"
    echo "  - Change commit hashes (all commits after the first modified one)"
    echo "  - Require force-push to update remote (if you want to push)"
    echo ""
    read -p "Do you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    echo ""
fi

# Create backup branch (mandatory on main/master, optional on other branches)
if [ "$IS_MAIN_BRANCH" = true ]; then
    # Mandatory backup on main/master
    BACKUP_BRANCH="backup-before-date-rewrite-$(date +%Y%m%d-%H%M%S)"
    git branch "$BACKUP_BRANCH"
    echo "✅ Backup branch created (mandatory): $BACKUP_BRANCH"
    echo ""
    echo "💾 You can restore with: git reset --hard $BACKUP_BRANCH"
    echo ""
else
    # Optional backup on other branches
    echo "💡 Tip: Consider creating a backup branch first:"
    echo "   git branch backup-before-date-rewrite"
    echo ""
    read -p "Create backup branch now? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        BACKUP_BRANCH="backup-before-date-rewrite-$(date +%Y%m%d-%H%M%S)"
        git branch "$BACKUP_BRANCH"
        echo "✅ Backup branch created: $BACKUP_BRANCH"
        echo ""
    fi
fi

# Function: generate random number between min and max
random() {
    local min=$1
    local max=$2
    echo $((RANDOM % (max - min + 1) + min))
}

# Build filter-branch command
FILTER_BRANCH_ARGS=("--env-filter")

# Add since filter if provided
if [ -n "${1:-}" ]; then
    FILTER_BRANCH_ARGS+=("--since=$1")
fi

# Execute filter-branch with date rewriting logic
# Note: Uses a portable date parsing approach that works on both macOS and Linux
git filter-branch "${FILTER_BRANCH_ARGS[@]}" '
random() {
    local min=$1
    local max=$2
    echo $((RANDOM % (max - min + 1) + min))
}

ORIGINAL_DATE="$GIT_AUTHOR_DATE"

# Extract timezone from original date (format: +HHMM or -HHMM)
# Git dates are typically in format: "YYYY-MM-DD HH:MM:SS +HHMM" or "YYYY-MM-DD HH:MM:SS -HHMM"
TIMEZONE=""
if [[ "$ORIGINAL_DATE" =~ ([+-][0-9]{4})([[:space:]]*)$ ]]; then
    # Extract timezone in format +HHMM or -HHMM (4 digits after sign)
    TIMEZONE="${BASH_REMATCH[1]}"
elif [[ "$ORIGINAL_DATE" =~ ([+-][0-9]{2}:[0-9]{2}) ]]; then
    # Convert +02:00 to +0200 (remove colon)
    TZ_PART="${BASH_REMATCH[1]}"
    TIMEZONE="${TZ_PART:0:3}${TZ_PART:4:2}"
else
    # Default to local timezone if not found
    if command -v gdate >/dev/null 2>&1; then
        TIMEZONE=$(gdate +%z 2>/dev/null | head -c 5 || echo "+0000")
    elif date +%z >/dev/null 2>&1; then
        TIMEZONE=$(date +%z 2>/dev/null | head -c 5 || echo "+0000")
    else
        TIMEZONE="+0000"
    fi
fi

# Ensure timezone is exactly 5 characters (+HHMM or -HHMM)
if [[ ! "$TIMEZONE" =~ ^[+-][0-9]{4}$ ]]; then
    TIMEZONE="+0000"
fi

# Parse original date - try multiple methods for cross-platform compatibility
# Extract date part directly from Git date format (YYYY-MM-DD HH:MM:SS +HHMM)
if [[ "$ORIGINAL_DATE" =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
    # Extract date part directly from regex
    DAY="${BASH_REMATCH[1]}"
    # Calculate day of week
    if command -v gdate >/dev/null 2>&1; then
        DOW=$(gdate -d "$DAY" +%u 2>/dev/null || echo "1")
    elif date -d "$DAY" >/dev/null 2>&1; then
        DOW=$(date -d "$DAY" +%u 2>/dev/null || echo "1")
    else
        DOW=$(date -j -f "%Y-%m-%d" "$DAY" +%u 2>/dev/null || echo "1")
    fi
else
    # Fallback: try to parse with date commands
    if command -v gdate >/dev/null 2>&1; then
        # GNU date (macOS with coreutils or Linux)
        DOW=$(gdate -d "$ORIGINAL_DATE" +%u 2>/dev/null || echo "1")
        DAY=$(gdate -d "$ORIGINAL_DATE" +%Y-%m-%d 2>/dev/null || gdate +%Y-%m-%d)
    elif date -d "1970-01-01" >/dev/null 2>&1; then
        # GNU date (Linux)
        DOW=$(date -d "$ORIGINAL_DATE" +%u 2>/dev/null || echo "1")
        DAY=$(date -d "$ORIGINAL_DATE" +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)
    else
        # BSD date (macOS) - try to parse with BSD date
        DOW=$(date -j -f "%Y-%m-%d %H:%M:%S %z" "$ORIGINAL_DATE" +%u 2>/dev/null || \
              date -j -f "%Y-%m-%d %H:%M:%S" "$ORIGINAL_DATE" +%u 2>/dev/null || \
              date +%u)
        DAY=$(date -j -f "%Y-%m-%d %H:%M:%S %z" "$ORIGINAL_DATE" +%Y-%m-%d 2>/dev/null || \
              date -j -f "%Y-%m-%d %H:%M:%S" "$ORIGINAL_DATE" +%Y-%m-%d 2>/dev/null || \
              date +%Y-%m-%d)
    fi
fi

# 3% commits at unusual hours (3-5 AM)
if [ $((RANDOM % 100)) -lt 3 ]; then
    H=$(random 3 5)
    M=$(random 0 59)
    S=$(random 0 59)
    # Format date with zero-padding for hours, minutes, seconds and timezone
    # Git format: YYYY-MM-DD HH:MM:SS +HHMM
    NEW_DATE=$(printf "%s %02d:%02d:%02d %s" "$DAY" "$H" "$M" "$S" "$TIMEZONE")
    # Validate format before exporting
    if [[ "$NEW_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]][0-9]{2}:[0-9]{2}:[0-9]{2}[[:space:]][+-][0-9]{4}$ ]]; then
        export GIT_AUTHOR_DATE="$NEW_DATE"
        export GIT_COMMITTER_DATE="$NEW_DATE"
    else
        # Fallback: use original date if format is invalid
        export GIT_AUTHOR_DATE="$ORIGINAL_DATE"
        export GIT_COMMITTER_DATE="$ORIGINAL_DATE"
    fi
    exit 0
fi

# Weekday (Monday-Friday) - Only outside work hours (9 AM - 5 PM)
if [ "$DOW" -le 5 ]; then
    PROB=$((RANDOM % 100))
    if [ "$PROB" -lt 70 ]; then
        # 70% chance: evening hours (18:00-23:59) - after work
        H=$(random 18 23)
        M=$(random 0 59)
        S=$(random 0 59)
    elif [ "$PROB" -lt 85 ]; then
        # 15% chance: early morning (06:00-08:59) - before work
        H=$(random 6 8)
        M=$(random 0 59)
        S=$(random 0 59)
    else
        # 15% chance: very late night (00:00-05:59) - late night coding
        H=$(random 0 5)
        M=$(random 0 59)
        S=$(random 0 59)
    fi

# Saturday - Weekend, more flexible hours but still realistic
elif [ "$DOW" -eq 6 ]; then
    PROB=$((RANDOM % 100))
    if [ "$PROB" -lt 25 ]; then
        # 25% chance: late morning (10:00-12:59) - relaxed weekend morning
        H=$(random 10 12)
    elif [ "$PROB" -lt 55 ]; then
        # 30% chance: afternoon (14:00-17:59) - weekend afternoon
        H=$(random 14 17)
    else
        # 45% chance: evening (19:00-23:59) - weekend evening
        H=$(random 19 23)
    fi
    M=$(random 0 59)
    S=$(random 0 59)

# Sunday - Weekend, similar to Saturday
else
    PROB=$((RANDOM % 100))
    if [ "$PROB" -lt 30 ]; then
        # 30% chance: late morning (10:00-13:59) - relaxed Sunday
        H=$(random 10 13)
    elif [ "$PROB" -lt 60 ]; then
        # 30% chance: afternoon (14:00-17:59) - Sunday afternoon
        H=$(random 14 17)
    else
        # 40% chance: evening (18:00-23:59) - Sunday evening
        H=$(random 18 23)
    fi
    M=$(random 0 59)
    S=$(random 0 59)
fi

# Format date with zero-padding for hours, minutes, seconds and timezone
# Git format: YYYY-MM-DD HH:MM:SS +HHMM
NEW_DATE=$(printf "%s %02d:%02d:%02d %s" "$DAY" "$H" "$M" "$S" "$TIMEZONE")
# Validate format before exporting
if [[ "$NEW_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]][0-9]{2}:[0-9]{2}:[0-9]{2}[[:space:]][+-][0-9]{4}$ ]]; then
    export GIT_AUTHOR_DATE="$NEW_DATE"
    export GIT_COMMITTER_DATE="$NEW_DATE"
else
    # Fallback: use original date if format is invalid
    export GIT_AUTHOR_DATE="$ORIGINAL_DATE"
    export GIT_COMMITTER_DATE="$ORIGINAL_DATE"
fi
' -- --all

# Clean up filter-branch backup refs (optional, saves space)
echo ""
echo "✅ Date rewriting completed!"
echo ""

# Get current branch again (in case it changed, though it shouldn't)
CURRENT_BRANCH_FINAL=$(git rev-parse --abbrev-ref HEAD)
if [[ "$CURRENT_BRANCH_FINAL" == "main" ]] || [[ "$CURRENT_BRANCH_FINAL" == "master" ]]; then
    echo "🚨 You are on MAIN/MASTER branch!"
    echo ""
    echo "📝 CRITICAL Next steps:"
    echo "  1. Review the changes: git log --oneline"
    echo "  2. Test that everything works: git status, run tests, etc."
    echo "  3. If something is wrong, restore immediately:"
    if [ -n "${BACKUP_BRANCH:-}" ]; then
        echo "     git reset --hard $BACKUP_BRANCH"
    else
        echo "     git reset --hard backup-before-date-rewrite-*"
    fi
    echo ""
    echo "  4. If everything is OK and you want to update remote:"
    echo "     ⚠️  WARNING: This will break other people's clones!"
    echo "     git push --force-with-lease origin $CURRENT_BRANCH_FINAL"
    echo ""
    echo "  5. Notify your team that they need to:"
    echo "     - Re-clone the repository, OR"
    echo "     - Reset their local branch: git fetch && git reset --hard origin/$CURRENT_BRANCH_FINAL"
    echo ""
    if [ -n "${BACKUP_BRANCH:-}" ]; then
        echo "🔄 Backup branch: $BACKUP_BRANCH"
        echo "   Keep this branch until you're 100% sure everything is OK!"
    fi
else
    echo "📝 Next steps:"
    echo "  1. Review the changes: git log --oneline"
    echo "  2. If satisfied, clean up backup refs: git for-each-ref --format='%(refname)' refs/original/ | xargs -n 1 git update-ref -d"
    echo "  3. If you want to push to remote (⚠️  DANGEROUS):"
    echo "     git push --force-with-lease origin $CURRENT_BRANCH_FINAL"
    echo ""
    if [ -n "${BACKUP_BRANCH:-}" ]; then
        echo "🔄 To undo (backup branch created):"
        echo "   git reset --hard $BACKUP_BRANCH"
    else
        echo "🔄 To undo (if you created a backup branch):"
        echo "   git reset --hard backup-before-date-rewrite-*"
    fi
    echo ""
fi

echo "⚠️  Remember: All commit hashes have changed. Anyone who cloned this repo"
echo "   will need to re-clone or reset their local copy."
