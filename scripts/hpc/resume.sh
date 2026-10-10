#!/bin/sh
# Resume campaigns on a running Ollama GPU job, keeping the tunnel alive; release the GPU at the end.
# Usage: JOB=<id> NODE=<host> PREFIX=fin sh scripts/hpc/resume.sh
set -u
cd "$(dirname "$0")/../.."
LOGIN=conduit.hpc.uni-saarland.de
keep_tunnel() {
  while :; do
    curl -s --max-time 5 http://localhost:11435/api/version >/dev/null 2>&1 || \
      ssh -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -L 11435:$NODE:11434 $LOGIN 2>/dev/null
    sleep 10
  done
}
keep_tunnel &
KEEPER=$!
sleep 5
caffeinate -i -s -d sh -c '
  MODELS=llama3.1:8b DOMAINS=clinical PULL_PER_MODEL=0 sh scripts/hpc/campaign.sh
  MODELS="llama3.3:70b qwen2.5:72b" DOMAINS="finance procurement clinical" PULL_PER_MODEL=1 sh scripts/hpc/campaign.sh
'
echo "campaign exit $?"
kill $KEEPER 2>/dev/null
ssh $LOGIN "condor_rm $JOB"
pkill -f "11435:$NODE"
