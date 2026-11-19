#!/usr/bin/env bash
# One command before shipping: every test in Chromium, the browser tests again in WebKit (iPhone's engine),
# then 390px screenshots of the key screens in both. Usage: tools/claude/check.sh [--quick] [--shots DIR]
# --quick skips WebKit and screenshots. Exit code = number of failing test runs.
cd "$(dirname "$0")/../.." || exit 99
QUICK=0; SHOTS=/tmp/foxboard-shots
while [ $# -gt 0 ]; do case "$1" in --quick) QUICK=1;; --shots) SHOTS="$2"; shift;; esac; shift; done
PWV=$(node -e "console.log(require('playwright/package.json').version)" 2>/dev/null || echo 1.63.0)
python3 -c "import playwright" 2>/dev/null || pip install -q "playwright==$PWV" >/dev/null 2>&1 || echo "! could not install python playwright"
# Chromium comes with the container (/opt/pw-browsers); WebKit lives in /opt/pw-webkit (environment setup) or gets installed here.
BR=${FOXBOARD_BROWSERS:-/tmp/foxboard-browsers}; mkdir -p "$BR"
for d in /opt/pw-browsers/* /opt/pw-webkit/*; do [ -e "$d" ] && [ ! -e "$BR/$(basename "$d")" ] && ln -s "$d" "$BR/"; done
if [ $QUICK = 0 ] && ! ls "$BR" | grep -q '^webkit-'; then
  echo "· installing WebKit (one time, ~1 min)"; PLAYWRIGHT_BROWSERS_PATH="$BR" python3 -m playwright install --with-deps webkit >/dev/null 2>&1 || echo "! WebKit install failed: iPhone checks skipped"
fi
export PLAYWRIGHT_BROWSERS_PATH="$BR"
fail=0; log=$(mktemp)
run(){ local eng=$1 t=$2; BROWSER=$eng timeout 900 python3 "$t" >"$log" 2>&1; local rc=$?
  local last; last=$(grep -v ' - - ' "$log" | grep -v '^\s*$' | tail -1 | cut -c1-90)
  if [ $rc = 0 ]; then echo "  ok    $eng  $(basename "$t")  $last"; else echo "  FAIL  $eng  $(basename "$t")  $last"; grep -E '^FAIL' "$log" | head -8 | sed 's/^/          /'; fail=$((fail+1)); fi; }
echo "Chromium (Android-like):"; for t in tests/test_*.py; do run chromium "$t"; done
if [ $QUICK = 0 ] && ls "$BR" | grep -q '^webkit-'; then
  echo "WebKit (iPhone):"; for t in $(grep -l "os.environ.get('BROWSER'" tests/test_*.py); do [ "$(basename "$t")" = test_site.py ] || run webkit "$t"; done
fi
[ $QUICK = 0 ] && { python3 tools/claude/shots.py "$SHOTS" && echo "Screenshots: $SHOTS (look at them)"; }

echo; [ $fail = 0 ] && echo "ALL GREEN" || echo "$fail failing"; rm -f "$log"; exit $fail
