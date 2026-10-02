"""Exact source/build/legal closure, distinct from generated build outputs."""
import hashlib
import json
import os
from pathlib import Path

AUDIT_EXCLUSIONS = {
    'NOTICE-EVIDENCE.json': 'self-reference: this manifest cannot hash itself',
    'NOTICE': 'contains the digest of NOTICE-EVIDENCE.json; independently hashed in returned record',
    'SOURCE.json': 'written by orchestrator after audit; must bind NOTICE and evidence independently',
}


def inventory(root):
    spec = json.loads((root / 'component.json').read_text())
    generated = {'build', 'dist', 'node_modules', '.git', 'scripts/__pycache__', 'test/__pycache__'}
    if spec['binding'] is None:
        generated |= {f'plugins/{member}.comp/internal' for member in spec['members']}
    result = {}
    def visit(directory):
        for p in sorted(directory.iterdir()):
            name = p.relative_to(root).as_posix()
            # Even allowed output directory roots must not redirect through symlinks.
            if p.is_symlink():
                raise RuntimeError(f'symlink in repository closure: {name}')
            if name in generated:
                if not p.is_dir():
                    raise RuntimeError(f'generated directory is not a directory: {name}')
                continue
            if p.is_dir():
                visit(p)
            elif p.is_file():
                result[name] = hashlib.sha256(p.read_bytes()).hexdigest()
            else:
                raise RuntimeError(f'nonregular input: {name}')
    if root.is_symlink():
        raise RuntimeError('symlink repository root')
    visit(root)
    return result


def verify_inputs(root):
    actual = inventory(root)
    if (root / 'NOTICE-EVIDENCE.json').exists():
        evidence = json.loads((root / 'NOTICE-EVIDENCE.json').read_text())
        if evidence['hash_exclusions'] != AUDIT_EXCLUSIONS:
            raise RuntimeError('unexpected audit hash exclusions')
        expected = evidence['files_sha256']
        actual = {k: v for k, v in actual.items() if k not in AUDIT_EXCLUSIONS}
    else:
        expected = json.loads((root / 'SOURCE-INPUTS.json').read_text())
        actual = {k: v for k, v in actual.items() if k not in ('SOURCE-INPUTS.json', 'NOTICE')}
    if actual != expected:
        raise RuntimeError(f'source/build/legal closure changed: added={sorted(actual.keys()-expected.keys())}; missing={sorted(expected.keys()-actual.keys())}; changed={sorted(k for k in actual.keys() & expected.keys() if actual[k] != expected[k])}')
