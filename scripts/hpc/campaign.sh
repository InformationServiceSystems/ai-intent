#!/bin/sh
# Four campaigns over the SSH tunnel on local port 11435: both domains, ten runs each,
# with llama3.1:8b (continuity with ER 2026) and llama3.3:70b (ROADMAP 3.1).
# Usage: sh scripts/hpc/campaign.sh   (after the tunnel is open and both models are pulled)
#        MODELS=llama3.1:8b sh scripts/hpc/campaign.sh   (one model only)
set -u
cd "$(dirname "$0")/../.."
export AI_INTENT_CASE_PAUSE=2 PYTHONUNBUFFERED=1
BASE=http://localhost:11435/v1
for model in ${MODELS:-llama3.1:8b llama3.3:70b}; do
  tag=$(echo "$model" | sed 's/llama3.1:8b/m8/; s/llama3.3:70b/m70/; s/qwen2.5:72b/q72/')
  for domain in ${DOMAINS:-finance procurement}; do
    echo "=== $model $domain $(date)"
    LLM_MODEL=$model python3 evaluation/run_parallel.py --workers 10 --prefix "${PREFIX:-c4}_${tag}_${domain}" \
      --base-url "$BASE" --deterministic-routing --domain "$domain" ${CASES:+--cases "$CASES"}
  done
done
echo "=== done $(date)"
