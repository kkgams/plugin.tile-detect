#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from legal import legal_files, verify_legal
from tooling import payload, verify_zip
root = Path(__file__).resolve().parents[1]
spec = json.loads((root / 'component.json').read_text())
version = (root / 'version.txt').read_text().strip()
artifacts = [p.replace('0.1.0.zip', version + '.zip') for p in spec['artifacts']]
dist = root / 'dist'
verify_legal(root)
legal = legal_files(root, required=True)
readable = [name for name in legal if '/' not in name]
required = artifacts + readable + ['LICENSES.zip']

def run(*args):
    subprocess.run(args, cwd=root, check=True)

run('python3', 'scripts/check-source.py')
if sys.argv[1] == 'stage':
    for artifact in artifacts:
        p = dist / artifact
        if not p.is_file() or p.stat().st_size == 0:
            raise FileNotFoundError(p)
        if artifact.endswith('.wasm'):
            run('python3', 'scripts/wasm-notices.py', 'embed', str(p), '--license', 'LICENSE', '--notice', 'NOTICE')
        else:
            # Rebuild ZIP from source before staging if legal texts changed.
            with zipfile.ZipFile(p) as z:
                if z.read('LICENSE') != (root / 'LICENSE').read_bytes() or z.read('NOTICE') != (root / 'NOTICE').read_bytes():
                    raise RuntimeError('ZIP licensing differs; rebuild before staging')
    for name in readable:
        (dist / name).write_bytes((root / name).read_bytes())
    with zipfile.ZipFile(dist / 'LICENSES.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in legal:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (root / name).read_bytes())
    (dist / 'SHA256SUMS').write_text(''.join(hashlib.sha256((dist / p).read_bytes()).hexdigest() + '  ' + p + '\n' for p in required))
actual = {p.name for p in dist.iterdir()}
if actual != set(required + ['SHA256SUMS']):
    raise RuntimeError(f'unexpected/incomplete candidate files: {actual}')
lines = (dist / 'SHA256SUMS').read_text().splitlines()
if [line.split('  ', 1)[1] for line in lines] != required:
    raise RuntimeError('Incomplete/unexpected release set')
for line in lines:
    digest, name = line.split('  ', 1)
    if hashlib.sha256((dist / name).read_bytes()).hexdigest() != digest:
        raise RuntimeError(f'candidate checksum differs: {name}')
for artifact in artifacts:
    if artifact.endswith('.wasm'):
        run('wasm-tools', 'validate', str(dist / artifact))
        run('python3', 'scripts/wasm-notices.py', 'verify', str(dist / artifact), '--license', 'LICENSE', '--notice', 'NOTICE')
    else:
        verify_zip(dist / artifact, payload(root))
with zipfile.ZipFile(dist / 'LICENSES.zip') as archive:
    if sorted(archive.namelist()) != sorted(legal):
        raise RuntimeError('Incomplete candidate legal bundle')
    for name in legal:
        if archive.read(name) != (root / name).read_bytes():
            raise RuntimeError(f'Candidate legal bundle differs: {name}')
for name in readable:
    if (dist / name).read_bytes() != (root / name).read_bytes():
        raise RuntimeError(f'candidate legal/source evidence differs: {name}')
# Run the supported runtime assertions on final notice-bearing bytes, not the pre-embed build.
if spec['slug'] in ('pack', 'random', 'sql'):
    run('npm', 'ci')
    for artifact in artifacts:
        run(str(root / 'node_modules/.bin/jco'), 'transpile', str(dist / artifact),
            '-o', f'build/jco/{artifact}', '--name', 'component')
    run('node', 'test/runtime.mjs')
