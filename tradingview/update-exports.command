#!/bin/bash
# Double-click this file to copy your newest TradingView "List of trades"
# exports (MNQ1! and MGC1!) from Downloads into the project. Then push in
# GitHub Desktop, and the dashboard shows the new stats on its next run.
cd "$(dirname "$0")/exports" || exit 1
for symbol in "MNQ1!" "MGC1!"; do
  newest=$(ls -t ~/Downloads/*"$symbol"*.csv 2>/dev/null | head -1)
  if [ -n "$newest" ]; then
    cp "$newest" .
    echo "Copied: $(basename "$newest")"
  else
    echo "No $symbol export found in Downloads."
  fi
done
echo
echo "Done. Now push in GitHub Desktop. You can close this window."
