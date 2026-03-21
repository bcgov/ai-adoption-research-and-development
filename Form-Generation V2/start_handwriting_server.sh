#!/usr/bin/env bash
# Start the Node handwriting server (uses local patched handwritten.js with lineWidth support).
# Run this in a terminal and leave it running; then in another terminal run:
#   python build_test_form.py 1 --complete-fill
#
# Server listens on http://localhost:8000

cd "$(dirname "$0")/handwriting-generator" || exit 1
node server-node.js
