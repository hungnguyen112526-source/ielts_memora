#!/usr/bin/env bash
# Build engine/reader/tailwind.css (cần Node). Không phải chạy khi deploy, file CSS đã được commit.
set -euo pipefail
cd "$(dirname "$0")"
npx --yes tailwindcss@3.4.17 -c tailwind.config.js -i input.css -o ../../engine/reader/tailwind.css --minify
