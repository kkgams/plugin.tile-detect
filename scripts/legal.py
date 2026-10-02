"""Owner source audit handoff: final releases require its complete readable evidence."""
import hashlib
import json
from inputs import verify_inputs
from pathlib import Path

LEGAL_ROOT_FILES = ('LICENSE', 'NOTICE', 'NOTICE-EVIDENCE.json', 'THIRD-PARTY-REVIEW.md', 'LICENSING.md')


def legal_files(root: Path, required=False):
    if not (root / 'NOTICE-EVIDENCE.json').is_file():
        if required:
            raise RuntimeError('Source-bound owner legal audit missing; release is blocked')
        return ['LICENSE', 'NOTICE', 'THIRD-PARTY-SOURCE.json']
    result = list(LEGAL_ROOT_FILES) + ['THIRD-PARTY-SOURCE.json']
    if not (root / 'LICENSES').is_dir():
        raise FileNotFoundError(root / 'LICENSES')
    result += [p.relative_to(root).as_posix() for p in sorted((root / 'LICENSES').rglob('*')) if p.is_file()]
    # These upstream terms are source-owned too, not replaced by the audit's comparisons.
    wasi = root / 'third_party/wasi-0.2.0'
    if wasi.is_dir():
        result += [p.relative_to(root).as_posix() for p in sorted(wasi.rglob('*'))
                   if p.is_file() and ('license' in p.name.lower() or p.name == 'W3C-Community-CLA.html')]
    if (root / 'MARKOV-UPSTREAM-ATTRIBUTIONS.md').is_file():
        result.append('MARKOV-UPSTREAM-ATTRIBUTIONS.md')
    for name in result:
        if not (root / name).is_file() or (root / name).is_symlink():
            raise FileNotFoundError(root / name)
    return result


def verify_legal(root: Path):
    verify_inputs(root)
    legal_files(root, required=True)
    raw = (root / 'NOTICE-EVIDENCE.json').read_bytes()
    evidence = json.loads(raw)
    if evidence['repository'] != json.loads((root / 'component.json').read_text())['name']:
        raise RuntimeError('Noncanonical source-bound evidence')
    if evidence['permission_blockers']:
        raise RuntimeError(f"Unresolved permission blockers: {evidence['permission_blockers']}")
    suffix = f'NOTICE-EVIDENCE.json SHA-256: {hashlib.sha256(raw).hexdigest()}\n'.encode()
    notice = (root / 'NOTICE').read_bytes()
    if not notice.endswith(suffix) or hashlib.sha256(notice[:-len(suffix)]).hexdigest() != evidence['notice_body_sha256']:
        raise RuntimeError('NOTICE does not bind exact audit evidence')
    # Audit was run before build: generated files are not silently recertified as source.
    for name, digest in evidence['files_sha256'].items():
        p = root / name
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'Source-bound legal evidence changed: {name}')
