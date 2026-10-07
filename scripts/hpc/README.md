# Running the evaluation suite against an HPC GPU node

The suite itself runs on the workstation; only the language model runs on the cluster. Ten independent runner processes share one Ollama server through an SSH tunnel, each with its own SQLite database and output prefix.

1. **Submit the Ollama job** on the login node (`ssh <user>@conduit.hpc.uni-saarland.de`):
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

The cluster accepts docker or container universe jobs only. If `condor_submit` fails with `SECMAN` errors, the scheduler is refusing connections; retry later rather than changing the submit file.
