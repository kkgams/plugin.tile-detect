#!/usr/bin/env python3
"""Standalone source builds; no dependency on monorepo make rules or hosts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from legal import legal_files
from inputs import verify_inputs
from tooling import payload, verify_zip

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
SPEC = json.loads(Path('component.json').read_text())


def run(*args, cwd=ROOT):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, check=True)


def build():
    verify_inputs(ROOT)
    Path('build').mkdir(exist_ok=True)
    Path('dist').mkdir(exist_ok=True)
    for member in SPEC['members']:
        source = ROOT / f'plugins/{member}.comp'
        gen = ROOT / f'build/{member}'
        gen.mkdir(exist_ok=True)
        world = SPEC['world']
        binding = SPEC['binding']
        artifact = ROOT / 'dist' / (f'plugin.{member}.wasm' if member == 'sql-vec' else f"plugin.{SPEC['slug']}.wasm")
        if binding is None:
            package = gen / 'package.wasm'
            run('wasm-tools', 'component', 'wit', source / 'wit', '--wasm', '-o', package)
            run('go', 'tool', 'wit-bindgen-go', 'generate', '--world', world, '--out', 'internal', package, cwd=source)
            run('tinygo', 'build', '-target=wasip2', '-opt=2', '-no-debug', '-o', artifact,
                '--wit-package', package, '--wit-world', world, 'main.go', cwd=source)
        else:
            run('wit-bindgen', 'c', source / 'wit', '-w', world, cwd=gen)
            inputs = [source / 'component.c']
            flags = []
            if SPEC['slug'] == 'markov-junior':
                obj = gen / 'markov.o.obj'
                run('odin', 'build', source / 'markov_junior', '-target:wasi_wasm32', '-build-mode:obj',
                    '--no-entry-point', '-o:speed', f'-out:{obj}')
                if not obj.is_file():
                    raise FileNotFoundError(obj)
                inputs.append(obj)
            if SPEC['slug'] == 'sql':
                inputs.append(source / 'vendor/sqlite3.c')
                flags += [f'-I{source / "vendor"}', f'-I{ROOT / "plugins/sql.comp/sql-common"}',
                          '-DSQLITE_THREADSAFE=0', '-DSQLITE_OMIT_LOAD_EXTENSION', '-DSQLITE_OMIT_WAL',
                          '-DSQLITE_TEMP_STORE=3', '-DSQLITE_DEFAULT_MEMSTATUS=0']
                if member == 'sql-vec':
                    inputs.append(source / 'vendor/sqlite-vec.c')
                    flags += ['-DGAMS_SQL_WITH_VEC', '-DSQLITE_CORE', '-DSQLITE_VEC_STATIC', '-DSQLITE_VEC_OMIT_FS']
            run('wasm32-wasip2-clang', '-o', artifact, '-mexec-model=reactor', f'-I{gen}', '-O2', '-DNDEBUG',
                *flags, gen / f'{binding}.c', *inputs, gen / f'{binding}_component_type.o', '-Wl,--strip-all')
        stripped = artifact.with_suffix('.strip')
        run('wasm-tools', 'strip', '-a', artifact, '-o', stripped)
        stripped.replace(artifact)
        run('wasm-tools', 'validate', artifact)
        with (gen / 'extracted.wit').open('w') as output:
            subprocess.run(['wasm-tools', 'component', 'wit', str(artifact)], stdout=output, check=True)
    if SPEC['slug'] == 'markov-junior':
        # Retain source compiler, resources, docs AND historical tooling. No fake compiled assets.
        archive = ROOT / f"dist/plugin.markov-junior-tooling-{Path('version.txt').read_text().strip()}.zip"
        expected = payload(ROOT)
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in expected.items():
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, data)
        verify_zip(archive, expected)


def test():
    run('python3', '-m', 'unittest', 'discover', '-s', 'test', '-p', 'test_*.py')
    build()
    run('python3', 'scripts/check-source.py')
    if SPEC['binding'] is None:
        run('go', 'test', './...', cwd=ROOT / f"plugins/{SPEC['source']}.comp")
        run('go', 'test', './...', cwd=ROOT / 'sdk')
    if SPEC['slug'] == 'markov-junior':
        for name in ('compiler', 'mjir-v1'):
            run('node', f'plugins/markov-junior.comp/test/{name}.mjs')
        import tempfile
        with tempfile.TemporaryDirectory(prefix='markov-tooling-test-') as temporary:
            extracted = Path(temporary)
            with zipfile.ZipFile(f"dist/plugin.markov-junior-tooling-{Path('version.txt').read_text().strip()}.zip") as archive:
                archive.extractall(extracted)
            for name in ('compiler', 'mjir-v1'):
                run('node', f'plugins/markov-junior.comp/test/{name}.mjs', cwd=extracted)
            run('node', 'script/markov-xml-to-mjir-json.mjs', 'examples/demo/ng/markov/cleanup.xml', 'cleanup.mjir.json', cwd=extracted)
            if not isinstance(json.loads((extracted / 'cleanup.mjir.json').read_text()), list):
                raise RuntimeError('compiler ZIP CLI output is not a byte array')
    if SPEC['slug'] in ('pack', 'random', 'sql'):
        run('npm', 'ci')
        for artifact in SPEC['artifacts']:
            run(ROOT / 'node_modules/.bin/jco', 'transpile', f'dist/{artifact}', '-o', f'build/jco/{artifact}', '--name', 'component')
        run('node', 'test/runtime.mjs')
    print('PASS: build/validation + stated unit/runtime tests only; see PREPARATION.md for coverage gaps.')


if __name__ == '__main__':
    {'build': build, 'test': test}[sys.argv[1]]()
