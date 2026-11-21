# Validation evidence

[CODEX_ENHANCEMENT_2026-11-21]

Source commit: `85de6f8588f4134d6714bda8b290cbc51d09a787`

GitHub Actions run: https://github.com/mbaglo/MechRoyale-Agent/actions/runs/44910472403

Observed completed/success for each step:

- Python 3.13 unit tests: ten passed.
- `docker build --platform linux/amd64 -t mechroyale-agent .`
- Official checker against the built image: passed with network disabled,
  1 CPU, 512 MB memory/no swap, uid 65534, read-only root filesystem,
  64 MB temporary filesystem, 128 process limit, all capabilities dropped,
  and read-only arena mounted at `/arena`.

Local repeat conformance check after the initialization fix:

```text
ready in 265 ms: name 'MechRoyale-Agent'
observations: 300  answered in time: 300  missed the 50 ms budget: 0 (0 came late)
answer time ms: p50 3.5  p90 7.0  p99 9.1  max 10.1
answers to older queued observations (dropped): 0  wrong tick: 0  bad lines: 0
PASS
```

No real matches were run. The official kit does not distribute a simulator;
the documented match route requires a signed-in competition submission.
No measured placement, survival, win rate, damage or official score exists yet.
Container protocol success does not establish competitive strength.
