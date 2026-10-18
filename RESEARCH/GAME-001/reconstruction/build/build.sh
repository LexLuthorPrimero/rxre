#!/bin/bash
# Build script for Madness Project Nexus Classic Reconstruction
# This script ensures reproducible builds with environment checks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=== Madness Project Nexus Classic Reconstruction Build ==="
echo "Project root: $PROJECT_ROOT"

# Check compiler
if ! command -v gcc &> /dev/null; then
    echo "ERROR: gcc not found. Please install gcc."
    exit 1
fi

echo "Using gcc: $(gcc --version | head -1)"

# Run make with default target
make all "$@"
