"""[ASTRA_ENHANCEMENT_2026-11-21] Compare two policies on the official recorded inputs."""
import argparse
from collections import Counter
import gzip
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.policy import Bot


def compare(baseline):
    archive = subprocess.check_output(['git', 'archive', '--format=zip', baseline, 'agent'], cwd=ROOT)
    kit = ROOT / 'official/mechfight-kit'
    with tempfile.TemporaryDirectory() as directory, gzip.open(kit / 'check/stream.jsonl.gz', 'rt') as stream:
        with zipfile.ZipFile(io.BytesIO(archive)) as source:
            source.extractall(directory)
        (Path(directory) / 'agent').rename(Path(directory) / 'reference_agent')
        sys.path.insert(0, directory)
        reference = importlib.import_module('reference_agent.policy').Bot
        hello = json.loads(next(stream))
        hello['map']['dir'] = str(kit / 'arena')
        before, after = reference(hello), Bot(hello)
        counts = Counter()
        for line in stream:
            obs = json.loads(line)
            if obs['type'] != 'obs':
                continue
            old, new = before.act(obs), after.act(obs)
            counts['observations'] += 1
            counts['mode_changes'] += before.mode != after.mode
            counts['target_changes'] += before.combat.target_id != after.combat.target_id
            for field in ('move', 'aim', 'fire', 'take', 'boost'):
                counts[field + '_changes'] += old.get(field) != new.get(field)
        return dict(baseline=baseline, recorded_input_counts=dict(counts))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('baseline')
    print(json.dumps(compare(parser.parse_args().baseline), indent=2))
