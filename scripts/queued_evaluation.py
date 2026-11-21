"""[CODEX_ENHANCEMENT_2026-11-21] One authorized, validated evaluation.

Uses the dedicated local browser. No credentials are read or exported. This is
development automation, excluded from the match image. Never selects a final.
"""
import json
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone
from urllib.request import urlopen

COMMIT = 'e45d9eac7e53861c6f6305bee8c1f875749a3f25'
REPO = 'https://github.com/mbaglo/MechRoyale-Agent'
CI = 'https://api.github.com/repos/mbaglo/MechRoyale-Agent/actions/runs/44928587769'
DEADLINE = datetime(2026,11,22,16,tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]
LOCAL = Path(os.environ.get('LOCALAPPDATA',str(ROOT))) / 'MechRoyaleBrowser'


def quota(text):
    match = re.search(r'\b([0-4]) of 4 left this hour\b',text,re.I)
    if not match:
        raise ValueError('Cannot determine live quota; no submission allowed')
    return int(match[1])


def scored(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if 'Scored' not in lines:
        return None
    i = lines.index('Scored')
    if i+1 >= len(lines):
        raise ValueError('Scored receipt has no score')
    value = float(lines[i+1])
    if not 0 <= value <= 15:
        raise ValueError('Score outside official range')
    return value


def main():
    LOCAL.mkdir(parents=True,exist_ok=True)
    # [CODEX_FIX_2026-11-21] Prevent two local watchers racing on one quota slot.
    lock = LOCAL/'evaluation.lock'
    try:
        fd = os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        print('An evaluation watcher lock already exists; no second watcher started.')
        return
    os.write(fd,str(os.getpid()).encode());os.close(fd)
    sys.path.insert(0,str(LOCAL/'tools'))
    from playwright.sync_api import sync_playwright
    state = dict(experiment='EXP-006',commit=COMMIT,repository=REPO,
                 submission_id=None,official_score=None,submission_attempts=0)
    previous = LOCAL/'evaluation-state.json'
    if previous.exists():
        old = json.loads(previous.read_text(encoding='utf-8'))
        if old.get('commit')==COMMIT:
            state['submission_attempts']=old.get('submission_attempts',0)
            state['submission_id']=old.get('submission_id')

    def save(status,**extra):
        state.update(status=status,observed_at=datetime.now(timezone.utc).isoformat(),**extra)
        temp = LOCAL/'evaluation-state.tmp'
        temp.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
        temp.replace(LOCAL/'evaluation-state.json')
        if status in ('Scored','Rejected','Failed'):
            (ROOT/'reports'/'EXP-006-live.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')

    save('starting')
    try:
        ci = json.load(urlopen(CI,timeout=20))
        if ci['head_sha'] != COMMIT or ci['status'] != 'completed' or ci['conclusion'] != 'success':
            raise RuntimeError('Exact candidate CI has not passed')
        expiry = time.monotonic()+45*60
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp('http://127.0.0.1:9223',timeout=15000)
            pages = [pg for c in browser.contexts for pg in c.pages if 'joinbuilders.org/buildathon/tracks/builders' in pg.url]
            if len(pages)!=1:
                raise RuntimeError('Cannot uniquely identify authorized competition tab')
            page = pages[0]
            while time.monotonic()<expiry:
                if datetime.now(timezone.utc)>=DEADLINE:
                    save('deadline reached; stopped');return
                page.reload(wait_until='domcontentloaded',timeout=30000)
                page.get_by_text("Your team's submissions",exact=True).wait_for(timeout=20000)
                body = page.locator('body').inner_text()
                receipt = page.get_by_text(COMMIT[:12],exact=False)
                if receipt.count():
                    card = receipt.first.locator('xpath=..')
                    text = card.inner_text()
                    match = re.search(r'BB-[A-F0-9]{8}',text)
                    if not match:
                        raise RuntimeError('Cannot identify candidate receipt')
                    state['submission_id'] = match[0]
                    value = scored(text)
                    if value is not None:
                        save('Scored',official_score=value,
                             entered_in_final='Entered in the final' in text)
                        return
                    if re.search(r'\bRejected\b',text):
                        save('Rejected');return
                    if re.search(r'\bFailed\b',text):
                        save('Failed');return
                    save('Scoring')
                else:
                    if state['submission_attempts']:
                        # An uncertain first click must never be retried.
                        raise RuntimeError('Submission attempted but no receipt; stopped without retry')
                    section = body.split("Your team's submissions",1)[1].split('Mech Royale\n',1)[0]
                    if re.search(r'\b(Scoring|Queued)\b',section):
                        save('waiting for existing evaluation')
                    elif quota(body)==0:
                        save('waiting for hourly quota',next_slot_reported='2026-11-21T12:28:00-05:00')
                    else:
                        # Guard again immediately before the irreversible click.
                        if datetime.now(timezone.utc)>=DEADLINE:
                            save('deadline reached; stopped');return
                        page.locator('input[name="repo"]').fill(REPO)
                        page.locator('input[name="commit"]').fill(COMMIT)
                        state['submission_attempts']=1
                        save('submitting once')
                        page.get_by_role('button',name='Submit',exact=True).click(timeout=15000)
                        page.get_by_text(COMMIT[:12],exact=False).first.wait_for(timeout=20000)
                        save('submitted; awaiting receipt refresh')
                        continue
                time.sleep(30)
        save('watcher time limit reached; stopped')
    except Exception as exc:
        save('stopped on error; no automatic retry',error=f'{type(exc).__name__}: {exc}')
    finally:
        lock.unlink(missing_ok=True)


if __name__=='__main__':
    main()
