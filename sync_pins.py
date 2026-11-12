#!/usr/bin/env python3
"""The revisions kicad2ems's extras install, against this checkout's submodules.

kicad2ems/pyproject.toml names the stack's other packages by revision (`pip install 'kicad2ems[qs]'` gets that
pcbqs, not the newest), so a release installs the stack it was tested with. This checkout is that stack: each
submodule at the commit the others were tested with. The two have to say the same, and nothing made them: the qs
extra once stayed 68 commits behind pcbqs, so the installer gave a pcbqs without its circuit engine.

    python sync_pins.py            # check: each pin against its submodule's HEAD; exit 1 when one differs
    python sync_pins.py --write    # write the submodules' HEADs into kicad2ems/pyproject.toml

A pin has to be a commit its repository has on GitHub, so one that is only here (not on a branch of origin) is
refused. The order when packages change together: commit and push the other packages, `sync_pins.py --write`,
commit and push kicad2ems, then pin the submodules in this repository.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYPROJECT = ROOT / 'kicad2ems' / 'pyproject.toml'
PIN = re.compile(r'(git\+https://github\.com/lowprocess/([\w.-]+?)(?:\.git)?@)([0-9a-f]{40})')


def git(repo, *args):
    return subprocess.run(['git', '-C', str(ROOT / repo), *args], capture_output=True, text=True).stdout.strip()


def pins(text):
    """{repository: the revisions its pins name} (an extra and its variant pin one repository twice)."""
    out = {}
    for _url, repo, sha in PIN.findall(text):
        out.setdefault(repo, set()).add(sha)
    return out


def main(argv):
    write = '--write' in argv
    text = PYPROJECT.read_text(encoding='utf-8')
    stale, refused = [], []
    for repo, shas in sorted(pins(text).items()):
        if not (ROOT / repo / '.git').exists():
            print(f"{repo}: pinned in kicad2ems but not a submodule here")
            continue
        head = git(repo, 'rev-parse', 'HEAD')
        behind = [git(repo, 'rev-list', '--count', f'{s}..HEAD') or '?' for s in sorted(shas)]
        if shas == {head}:
            print(f"{repo}: {head[:7]}, as pinned")
            continue
        pushed = bool(git(repo, 'branch', '-r', '--contains', head))
        print(f"{repo}: pinned {', '.join(s[:7] for s in sorted(shas))}, {' / '.join(behind)} commit(s) behind its HEAD "
              f"{head[:7]}" + ('' if pushed else ' (which is not on origin yet: push it first)'))
        (stale if pushed else refused).append((repo, head))
    if write and stale:
        for repo, head in stale:
            text = re.sub(r'(git\+https://github\.com/lowprocess/' + re.escape(repo) + r'(?:\.git)?@)[0-9a-f]{40}',
                          lambda m: m.group(1) + head, text)
        PYPROJECT.write_text(text, encoding='utf-8')
        print(f"wrote {PYPROJECT.relative_to(ROOT)}: {', '.join(f'{r} {h[:7]}' for r, h in stale)}")
        stale = []
    return 1 if stale or refused else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
