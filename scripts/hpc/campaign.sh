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
  if [ "${PULL_PER_MODEL:-0}" = "1" ]; then
    # Pull just before use and delete afterwards, so three large models fit the job's disk request.
    curl -s --max-time 3000 http://localhost:11435/api/pull -d "{\"name\":\"$model\",\"stream\":false}" | grep -q success || { echo "pull $model failed"; exit 1; }
  fi
  for domain in ${DOMAINS:-finance procurement}; do
    echo "=== $model $domain $(date)"
    LLM_MODEL=$model python3 evaluation/run_parallel.py --workers 10 --prefix "${PREFIX:-c4}_${tag}_${domain}" \
      --base-url "$BASE" --deterministic-routing --domain "$domain" ${CASES:+--cases "$CASES"}
  done
  if [ "${PULL_PER_MODEL:-0}" = "1" ]; then
    curl -s -X DELETE http://localhost:11435/api/delete -d "{\"name\":\"$model\"}" >/dev/null
  fi
done
echo "=== done $(date)"
