# Environment Report (example)

This is a checked-in template showing the expected shape of the generated
`reports/environment-report.md`. The real, generated report is gitignored
because it contains point-in-time host details (exact free disk space,
current aircraft counts, etc.) that would otherwise churn on every commit.

Generate the real report with:

```bash
scripts/check_environment.sh
python3 scripts/probe_readsb.py --json-out reports/environment-report.json
```

## Summary

| Check | Result |
|---|---|
| OS / CPU (x86-64) | PASS |
| Memory / disk | PASS |
| Container runtime (Docker) | WARN / UNKNOWN until installed |
| readsb connectivity | PASS |
| Receiver location | PASS |
| Time sync | PASS |
| Network / ports | PASS |
| Existing services unaffected | PASS |

## Details

### A. OS and CPU
- Architecture: x86_64
- Distribution: (from /etc/os-release)
- Kernel: (uname -r)
- CPU cores: (nproc)

### B. Memory and disk
- Available memory: X GiB (pass threshold: >= 1 GiB, recommended >= 2 GiB)
- Free disk at deployment path: X GB (pass threshold: >= 10 GB, recommended >= 30 GB)
- Free inodes: X%

### C. Container runtime
- Docker version: (docker --version)
- Compose version: (docker compose version)
- Current user in docker group: yes/no

### D. readsb connectivity
- URL tried: http://127.0.0.1/tar1090/data/aircraft.json
- HTTP status / latency: 200 / X ms
- Top-level fields present: now, messages, aircraft
- Per-aircraft field availability: hex 100%, lat/lon X%, ...
- Two fetches ~12s apart: now/messages advanced -> PASS

### E. Receiver location
- lat, lon (rounded to 1 decimal): X.X, X.X

### F. Time
- Server time vs UTC offset: +X
- NTP synchronized: yes/no
- Clock skew vs readsb `now`: +X.XX s (WARN > 60s, FAIL > 300s)

### G. Network and ports
- Candidate app port free: yes/no
- No conflict with existing readsb/tar1090/fr24feed ports

### H. Existing services
- readsb / tar1090 / fr24feed active before and after check: yes/yes
