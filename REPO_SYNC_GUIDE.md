# Repository Synchronization Guide

This repository is mirrored between two Git services:
- **Git Kvant** (origin): `https://git.kvant.cloud/michele_smaldone/phoenix-widget-backend.git`
- **GitHub** (github): `https://github.com/MicheleSmaldone/phoenix-widget-backend.git`

## Quick Synchronization

### Using the Automated Script
```bash
./sync-repos.sh
```

### Manual Synchronization

#### Option 1: Push to Both Remotes Simultaneously
```bash
# Commit your changes first
git add .
git commit -m "Your commit message"

# Push to both remotes
git push origin main
git push github main
```

#### Option 2: Push to All Remotes at Once
```bash
# Set up push to all remotes (one-time setup)
git remote set-url --add --push origin https://git.kvant.cloud/michele_smaldone/phoenix-widget-backend.git
git remote set-url --add --push origin https://github.com/MicheleSmaldone/phoenix-widget-backend.git

# Now git push origin main will push to both
git push origin main
```

## Daily Workflow

1. **Make your changes** and commit locally
2. **Sync both repositories** using one of the methods above
3. Both repositories will always stay in sync

## Checking Repository Status

```bash
# View configured remotes
git remote -v

# Check if repos are in sync
git fetch origin
git fetch github
git log --oneline --graph --all
```

## Troubleshooting

### If GitHub authentication fails:
- Make sure you're using a Personal Access Token, not password
- Update your stored credentials: `git config --global credential.helper store`

### If repositories get out of sync:
```bash
# Fetch latest from both
git fetch origin
git fetch github

# Check differences
git log origin/main..github/main  # commits in github but not in origin
git log github/main..origin/main  # commits in origin but not in github
```

## Branch Management

For feature branches:
```bash
# Create and work on feature branch
git checkout -b feature/new-feature

# Push to both remotes when ready
git push origin feature/new-feature
git push github feature/new-feature
```
