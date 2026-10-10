#!/bin/sh
# Wait for an Ollama GPU job, open the tunnel, pull the models, run the campaigns, release the GPU.
# Usage: JOB=<ClusterId> MODELS="llama3.1:8b llama3.3:70b" DOMAINS="clinical" sh scripts/hpc/run_on_gpu.sh
set -u
cd "$(dirname "$0")/../.."
LOGIN=conduit.hpc.uni-saarland.de
while :; do
  out=$(ssh -o ConnectTimeout=15 $LOGIN "condor_q $JOB -af JobStatus RemoteHost" 2>/dev/null)
  st=$(echo "$out" | awk '{print $1}')
  [ "$st" = "2" ] && break
  [ "$st" = "5" ] && { echo "job $JOB held"; exit 1; }
  [ -z "$st" ] && { echo "job $JOB not in queue"; exit 1; }
  sleep 30
done
NODE=$(echo "$out" | awk '{print $2}' | sed 's/.*@//')
case "$NODE" in *.uni-saarland.de) ;; *) echo "unexpected node '$NODE'"; exit 1;; esac
echo "node $NODE"
for i in $(seq 1 30); do ssh $LOGIN "curl -s --max-time 5 http://$NODE:11434/api/version" | grep -q version && break; sleep 10; done
ssh -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 11435:$NODE:11434 $LOGIN || exit 1
if [ "${PULL_PER_MODEL:-0}" != "1" ]; then
  for m in $MODELS; do
    curl -s --max-time 3000 http://localhost:11435/api/pull -d "{\"name\":\"$m\",\"stream\":false}" | grep -q success || { echo "pull $m failed"; exit 1; }
  done
fi
caffeinate -i -s sh scripts/hpc/campaign.sh
echo "campaign exit $?"
ssh $LOGIN "condor_rm $JOB"
pkill -f "11435:$NODE"
