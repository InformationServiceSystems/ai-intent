# Running the evaluation suite against an HPC GPU node

The suite itself runs on the workstation; only the language model runs on the cluster. Ten independent runner processes share one Ollama server through an SSH tunnel, each with its own SQLite database and output prefix.

1. **Submit the Ollama job** on a login node. Both `conduit` and `conduit2` run a scheduler; if one refuses connections with `SECMAN` errors, use the other (on 7 October 2026 conduit's spool partition was full and its scheduler crash-looped, while conduit2 worked):
   ```bash
   mkdir -p ~/ai-intent-hpc && cp ollama-aiintent.sub ~/ai-intent-hpc/ && cd ~/ai-intent-hpc
   condor_submit ollama-aiintent.sub
   condor_q -nobatch -af:h ClusterId JobStatus RemoteHost     # wait for JobStatus 2 and a RemoteHost
   ```
2. **Pull the model once** the server is up (models persist in `~/.ollama`):
   ```bash
   NODE=$(condor_q -af RemoteHost | sed 's/.*@//')
   OLLAMA_HOST=$NODE:11434 ~/bin/ollama pull llama3.1:8b
   ```
3. **Open the tunnel** from the workstation (local port 11435, so a local Ollama on 11434 is untouched):
   ```bash
   ssh -N -L 11435:$NODE:11434 <user>@conduit.hpc.uni-saarland.de &
   curl -s http://localhost:11435/api/tags
   ```
4. **Run the workers**:
   ```bash
   python evaluation/run_parallel.py --workers 10 --prefix ufo_hpc --base-url http://localhost:11435/v1
   python evaluation/paper2_analysis.py --prefix ufo_hpc
   ```
   Worker `i` writes `evaluation/ufo_hpc_p{i}_results_*_run1.json`, its sessions under `evaluation/sessions/`, its log under `evaluation/logs/`, and its database under `data/sessions_ufo_hpc_p{i}.db`.
5. **Release the GPU** when done: `condor_rm <ClusterId>`.

The cluster accepts docker or container universe jobs only. If `condor_submit` fails with `SECMAN` errors, the scheduler is refusing connections; check `/var/log/condor/MasterLog` on that login node for the reason (a full spool disk shows as `errno = 28`) and submit on the other login node.

HTCondor 24.12 ignores the `mount =` line (it warns that the line is unused), so the model is pulled into the container's own storage and must be pulled again for each new job. That costs a few minutes per job and is acceptable for this workload.
