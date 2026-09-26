---
name: docker-desktop-disk-full-error-can-outlive-free-space
description: Docker Desktop may remain stuck with a stopped VM after a disk-full error even when the host later has free space; preserve Docker.raw and named volumes during recovery.
metadata: { type: gotcha }
---
On 2026-09-23, Docker Desktop's backend log reported `write .../Data/log/vm/init.log: no space left on device`, stopped the VM, and displayed a disk-full error. Later the host showed about 9.9 GiB free, but `docker desktop status` still timed out and FinSight ports 5442/9100 remained closed. A normal Docker Desktop stop/restart hung on long-lived GUI/backend processes. After verifying the VM had stopped and the backend was not holding `Docker.raw`, a process-only stop of the stuck Docker Desktop tree followed by `docker desktop start` restored the engine. The original `valuation_pgdata` and `valuation_miniodata` volumes remained present; the Batch 15 persistence verifier found its existing Postgres records and MinIO objects intact.

**Why:** More free host space alone did not clear Docker Desktop's error state. Static catalog hashes and passing tests could not prove the live API while the engine was down.

**How to detect / apply:** Check `df -h`, Docker Desktop's backend log, `docker desktop status`, and the project service ports. First try the normal app start/stop path. If the VM is confirmed stopped and graceful stop is stuck, validate exact Docker Desktop process identities before a process-only restart; never remove or reset `Docker.raw` or named volumes to clear the error. Confirm engine `running`, container health, volume names, and actual Postgres/MinIO records afterward. The host disk was still 98% used after recovery, so treat future disk pressure as a separate operational risk.
