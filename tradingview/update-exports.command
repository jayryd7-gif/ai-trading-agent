#!/bin/bash
# Double-click this file after exporting the "List of trades" from your
# TradingView charts (MNQ1! and MGC1!). It copies the newest exports from
# Downloads into the project, saves them in a commit, and opens GitHub
# Desktop so you only have to click "Push origin".
cd "$(dirname "$0")/.." || exit 1
copied=0
for symbol in "MNQ1!" "MGC1!"; do
  newest=$(ls -t ~/Downloads/*"$symbol"*.csv 2>/dev/null | head -1)
  if [ -n "$newest" ]; then
    cp "$newest" tradingview/exports/
    echo "Copied: $(basename "$newest")"
    copied=1
  else
    echo "No $symbol export found in Downloads."
  fi
done
if [ "$copied" = 1 ]; then
  git add tradingview/exports
  git commit -q -m "Update TradingView exports $(date +%F)" && echo "Saved in a commit."
  open -a "GitHub Desktop" .
  echo
  echo "Done. In GitHub Desktop, click Push origin. You can close this window."
else
  echo
  echo "Nothing to copy. Export the List of trades in TradingView first."
fi
