"""[CODEX_ENHANCEMENT_2026-11-21] Replay-only diagnostics, never game scores."""
import gzip
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agent.policy import Bot


def main():
    kit = ROOT/'official'/'mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f:
        messages = [json.loads(line) for line in f]
    hello = messages[0]
    hello['map']['dir'] = str(kit/'arena')
    bot = Bot(hello)
    samples, modes = [], {}
    for obs in messages:
        if obs['type'] != 'obs':
            continue
        start = time.perf_counter()
        bot.act(obs)
        samples.append((time.perf_counter()-start)*1000)
        modes[bot.mode] = modes.get(bot.mode,0)+1
    ordered = sorted(samples)
    result = dict(kind='recorded-input decision benchmark; NOT a simulation', observations=len(samples),
                  decision_ms=dict(mean=statistics.mean(samples),p50=statistics.median(samples),p99=ordered[int(.99*len(samples))],maximum=max(samples)),
                  modes=modes, full_matches=0, average_placement=None, survival_duration=None, win_rate=None,
                  damage_received=None, damage_dealt=None, official_score=None,
                  blockers=['Official kit provides no simulator; official scoring requires track submission.',
                            'Docker unavailable on development host; container sandbox validation pending.'])
    (ROOT/'reports'/'benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
