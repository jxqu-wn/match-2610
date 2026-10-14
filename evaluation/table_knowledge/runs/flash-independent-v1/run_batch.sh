#!/usr/bin/env bash
# Run the Deepseek Flash annotator through pi for one batch.
set -u
BATCH="${1:?batch id required}"
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../../../.." && pwd)"
PROMPT="$DIR/prompts/$BATCH.md"
OUT="$DIR/responses/$BATCH.json"
LOG="$DIR/logs/$BATCH.log"
START=$(date +%s)
cd "$ROOT"
pi --print \
  --model deepseek/deepseek-flash \
  --thinking high \
  --no-tools --no-session --no-context-files --no-extensions \
  --no-skills --no-prompt-templates --no-mcp --no-approve \
  --system-prompt "$ROOT/evaluation/table_knowledge/system_prompt.md" \
  "@$PROMPT" > "$OUT" 2> "$LOG"
RC=$?
END=$(date +%s)
echo "$BATCH rc=$RC seconds=$((END-START)) bytes=$(wc -c < "$OUT")" | tee -a "$DIR/logs/run.log"
exit $RC
