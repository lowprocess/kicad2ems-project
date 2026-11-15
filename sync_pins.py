#!/usr/bin/env python3
"""The revisions kicad2ems's extras install, against this checkout's submodules.

kicad2ems/pyproject.toml names the stack's other packages by revision (`pip install 'kicad2ems[qs]'` gets that
pcbqs, not the newest), so a release installs the stack it was tested with. This checkout is that stack: each
submodule at the commit the others were tested with. The two have to say the same, and nothing made them: the qs
extra once stayed 68 commits behind pcbqs, so the installer gave a pcbqs without its circuit engine.

    python sync_pins.py            # check: each pin against its submodule's HEAD; exit 1 when one differs
    python sync_pins.py --write    # write the submodules' HEADs into kicad2ems/pyproject.toml

emsdev changes seldom and is named by five packages, so it is pinned by its release tag
(emsdev/archive/refs/tags/vX.Y.Z.zip), the same in all five: this checks that, and says when main is past it.

The KiCad plugin's environment (kicad2ems-ipc/plugin/requirements.txt) names kicad2ems, kicad2ems-gui, gfdtd and
kicad2ems-fdtd by archive URLs of their commits (archive/<sha>.zip): those are checked and written the same way
(R-C16: they had stayed at a month-old stack).

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
PLUGIN_REQS = ROOT / 'kicad2ems-ipc' / 'plugin' / 'requirements.txt'
ARCHIVE = re.compile(r'(https://github\.com/lowprocess/([\w.-]+)/archive/)([0-9a-f]{40})(\.zip)')


def git(repo, *args):
    return subprocess.run(['git', '-C', str(ROOT / repo), *args], capture_output=True, text=True).stdout.strip()


def pins(text, pattern=PIN):
    """{repository: the revisions its pins name} (an extra and its variant pin one repository twice)."""
    out = {}
    for m in pattern.finditer(text):
        out.setdefault(m.group(2), set()).add(m.group(3))
    return out


TAGGED = re.compile(r'emsdev @ https://github\.com/lowprocess/emsdev/archive/refs/tags/(v[\w.]+)\.zip')
USERS = ('kicad2ems', 'pcbqs', 'mom25d', 'gfdtd', 'kicad2ems-fdtd',    # the pyprojects that name emsdev, and
         'kicad2ems/docs/requirements.txt')                       # the docs build's requirements


def emsdev_pins():
    """emsdev is pinned by release tag, the same in every pyproject that names it (pip refuses two URLs for one
    package): None when it is, else what is wrong. A release past the tag is said, not an error."""
    tags = {}
    for repo in USERS:
        path = ROOT / repo if repo.endswith('.txt') else ROOT / repo / 'pyproject.toml'
        text = path.read_text(encoding='utf-8')
        found = TAGGED.findall(text)
        if 'lowprocess/emsdev' in text and not found:
            return f"emsdev: {path.relative_to(ROOT)} does not pin it by a release tag (archive/refs/tags/vX.Y.Z.zip)"
        tags.update({repo: t for t in found})
    if len(set(tags.values())) != 1:
        return "emsdev: the pyprojects name different tags: " + ', '.join(f"{r} {t}" for r, t in sorted(tags.items()))
    tag = next(iter(tags.values()))
    if not git('emsdev', 'ls-remote', '--tags', 'origin', f'refs/tags/{tag}'):
        return f"emsdev: {tag} is not a tag on origin (tag and push it first)"
    ahead = git('emsdev', 'rev-list', '--count', f'{tag}..HEAD')
    print(f"emsdev: {tag} in all {len(tags)} of its pins" + (f" ({ahead} commit(s) on main since: a new tag pins them)"
                                                          if ahead not in ('', '0') else ''))
    return None


def main(argv):
    write = '--write' in argv
    wrong = emsdev_pins()
    if wrong:
        print(wrong)
    bad = sync(PYPROJECT, PIN, write, 'kicad2ems')
    if PLUGIN_REQS.exists():
        bad = sync(PLUGIN_REQS, ARCHIVE, write, 'the KiCad plugin') or bad
    return 1 if bad or wrong else 0


def sync(path, pattern, write, who):
    """Check (and with write, update) one file's pins against the submodules' HEADs; True while one is wrong."""
    text = path.read_text(encoding='utf-8')
    stale, refused = [], []
    for repo, shas in sorted(pins(text, pattern).items()):
        if not (ROOT / repo / '.git').exists():
            print(f"{repo}: pinned in {who} but not a submodule here")
            continue
        head = git(repo, 'rev-parse', 'HEAD')
        behind = [git(repo, 'rev-list', '--count', f'{s}..HEAD') or '?' for s in sorted(shas)]
        if shas == {head}:
            print(f"{repo}: {head[:7]}, as pinned")
            continue
        pushed = bool(git(repo, 'branch', '-r', '--contains', head))
        print(f"{repo}: pinned in {who} {', '.join(s[:7] for s in sorted(shas))}, {' / '.join(behind)} commit(s) "
              f"behind its HEAD {head[:7]}" + ('' if pushed else ' (which is not on origin yet: push it first)'))
        (stale if pushed else refused).append((repo, head))
    if write and stale:
        for repo, head in stale:
            text = pattern.sub(lambda m: m.group(1) + (head if m.group(2) == repo else m.group(3))
                               + (m.group(4) if m.lastindex >= 4 else ''), text)
        path.write_text(text, encoding='utf-8')
        print(f"wrote {path.relative_to(ROOT)}: {', '.join(f'{r} {h[:7]}' for r, h in stale)}")
        stale = []
    return bool(stale or refused)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
