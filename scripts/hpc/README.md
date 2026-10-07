# Running the evaluation suite against an HPC GPU node

The suite itself runs on the workstation; only the language model runs on the cluster. Ten independent runner processes share one Ollama server through an SSH tunnel, each with its own SQLite database and output prefix.

1. **Submit the Ollama job** on a login node. Both `conduit` and `conduit2` run a scheduler; if one refuses connections with `SECMAN` errors, use the other (on 7 October 2026 conduit's spool partition was full and its scheduler crash-looped, while conduit2 worked):
   ```bash
   mkdir -p ~/ai-intent-hpc && cp ollama-aiintent.sub ~/ai-intent-hpc/ && cd ~/ai-intent-hpc
   condor_submit ollama-aiintent.sub
   condor_q -nobatch -af:h ClusterId JobStatus RemoteHost     # wait for JobStatus 2 and a RemoteHost
   ```
2. **Pull the model** once the server answers (the model store lives in the container's `/tmp`, so this is repeated per job and takes a few minutes):
   ```bash
   NODE=$(condor_q -af RemoteHost | sed 's/.*@//')
   curl -X POST http://$NODE:11434/api/pull -d '{"name":"llama3.1:8b","stream":false}'
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

Three things that did not work on 7 October 2026, so the submit file avoids them: the container universe accepts only local `.sif` images (`apptainer pull` builds one, but the docker universe was quicker); the docker universe's default bridge network makes port 11434 unreachable from the login node, hence `docker_network_type = host`; and the container cannot write to the NFS home while HTCondor forces `HOME` there, hence the overridden entrypoint that sets `HOME=/tmp`. The `mount =` keyword is ignored by HTCondor 24.12. Current Ollama builds drop V100 and P100 cards, so the requirements exclude them.
