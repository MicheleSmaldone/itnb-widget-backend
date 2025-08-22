#!/bin/bash

# Repository Synchronization Script
# This script keeps git kvant (origin) and GitHub (github) repositories in sync

echo "🔄 Starting repository synchronization..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a git repository!"
    exit 1
fi

# Check current branch
CURRENT_BRANCH=$(git branch --show-current)
print_status "Current branch: $CURRENT_BRANCH"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    print_warning "You have uncommitted changes. Please commit or stash them first."
    git status --porcelain
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Fetch from both remotes
print_status "Fetching from git kvant (origin)..."
git fetch origin

print_status "Fetching from GitHub..."
git fetch github

# Push current branch to both remotes
print_status "Pushing $CURRENT_BRANCH to git kvant (origin)..."
if git push origin $CURRENT_BRANCH; then
    print_success "Pushed to git kvant successfully!"
else
    print_error "Failed to push to git kvant!"
    exit 1
fi

print_status "Pushing $CURRENT_BRANCH to GitHub..."
if git push github $CURRENT_BRANCH; then
    print_success "Pushed to GitHub successfully!"
else
    print_error "Failed to push to GitHub!"
    exit 1
fi

print_success "✅ Repositories synchronized successfully!"
print_status "Both git kvant and GitHub are now up to date."
