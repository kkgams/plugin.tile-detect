"""Offline source/build and publication regressions; no runtime claims/network."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from inputs import inventory, verify_inputs, AUDIT_EXCLUSIONS
from legal import verify_legal
from tooling import payload, verify_zip
from publication import policy, verify_public, api


def audit_fixture(root):
    (root / 'component.json').write_text(json.dumps({'name': 'plugin.markov-junior', 'slug': 'markov-junior', 'binding': 'markov_junior_plugin', 'members': ['markov-junior'], 'artifacts': ['plugin.markov-junior-tooling-0.1.0.zip']}))
    (root / 'version.txt').write_text('0.1.0\n')
    for name in ('LICENSE', 'THIRD-PARTY-SOURCE.json', 'THIRD-PARTY-REVIEW.md', 'LICENSING.md', 'README.md', 'LICENSES/terms.txt', 'plugins/markov-junior.comp/markov_junior/main.odin', 'packages/util/markov-junior/compiler.js', 'examples/demo/ng/markov/demo.xml'):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('reviewed bytes')
    evidence = {'repository': 'plugin.markov-junior', 'hash_exclusions': AUDIT_EXCLUSIONS, 'permission_blockers': [], 'files_sha256': inventory(root), 'notice_body_sha256': hashlib.sha256(b'notice\n').hexdigest()}
    raw = json.dumps(evidence).encode()
    (root / 'NOTICE-EVIDENCE.json').write_bytes(raw)
    (root / 'NOTICE').write_text('notice\nNOTICE-EVIDENCE.json SHA-256: ' + hashlib.sha256(raw).hexdigest() + '\n')


def write_zip(path, files, modes=None):
    with zipfile.ZipFile(path, 'w') as z:
        for name, data in files.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (modes or {}).get(name, 0o100644) << 16
            z.writestr(info, data)


class InputTests(unittest.TestCase):
    def test_exact_inputs_after_build_and_added_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            audit_fixture(root)
            for name in ('build/compiled.o', 'dist/plugin.wasm', 'node_modules/tool/cache'):
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('generated')
            verify_legal(root)
            for name in ('plugins/markov-junior.comp/markov_junior/extra.odin', 'packages/util/markov-junior/extra.js', 'examples/demo/ng/markov/extra.xml', 'LICENSES/new.txt', 'plugins/markov-junior.comp/nested/build/extra.odin'):
                with self.subTest(name=name):
                    p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('unreviewed')
                    with self.assertRaises(RuntimeError): verify_legal(root)
                    p.unlink()

    def test_symlink_parents_and_named_outputs(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            root = Path(d); audit_fixture(root)
            for name in ('plugins/markov-junior.comp/nested/build', 'packages/util/markov-junior', 'LICENSES', 'examples/demo/ng/markov', 'build'):
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True)
                saved = p.with_name(p.name + '.saved')
                existed = p.exists()
                if existed: p.rename(saved)
                p.symlink_to(outside, target_is_directory=True)
                with self.subTest(name=name), self.assertRaises(RuntimeError): verify_inputs(root)
                p.unlink()
                if existed: saved.rename(p)

    def test_unaudited_inventory_and_go_generated_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'component.json').write_text(json.dumps({'binding': None, 'members': ['scaler']}))
            original = inventory(root)
            (root / 'SOURCE-INPUTS.json').write_text(json.dumps(original))
            p = root / 'plugins/scaler.comp/internal/generated.go'; p.parent.mkdir(parents=True); p.write_text('generated')
            verify_inputs(root)
            p = root / 'plugins/scaler.comp/build/extra.go'; p.parent.mkdir(); p.write_text('unreviewed')
            with self.assertRaises(RuntimeError): verify_inputs(root)


class ZipTests(unittest.TestCase):
    def test_candidate_cli_rejects_recomputed_checksum_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copytree(Path(__file__).resolve().parents[1] / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            audit_fixture(root)
            dist = root / 'dist'; dist.mkdir()
            archive = dist / 'plugin.markov-junior-tooling-0.1.0.zip'
            files = payload(root)
            write_zip(archive, files)
            subprocess.run([sys.executable, 'scripts/candidate.py', 'stage'], cwd=root, check=True, capture_output=True)
            files['packages/util/markov-junior/compiler.js'] += b'\n// unreviewed executable\n'
            write_zip(archive, files)
            sums = dist / 'SHA256SUMS'
            sums.write_text('\n'.join(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name if line.endswith('  ' + archive.name) else line for line in sums.read_text().splitlines()) + '\n')
            result = subprocess.run([sys.executable, 'scripts/candidate.py', 'verify'], cwd=root, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('ZIP source bytes differ', result.stderr)

    def test_executable_tamper_recomputed_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); audit_fixture(root)
            files = payload(root); archive = root / 'candidate.zip'
            write_zip(archive, files); verify_zip(archive, files)
            tampered = dict(files); tampered['packages/util/markov-junior/compiler.js'] = b'tampered executable'
            write_zip(archive, tampered)
            (root / 'SHA256SUMS').write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  candidate.zip\n')
            with self.assertRaises(RuntimeError): verify_zip(archive, files)

    def test_extra_missing_duplicate_symlink_and_crc(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'tool.zip'; files = {'compiler.js': b'UNIQUE-COMPILER-BYTES'}
            for bad in ({**files, '../extra.js': b'extra'}, {}):
                write_zip(path, bad)
                with self.assertRaises(RuntimeError): verify_zip(path, files)
            write_zip(path, files, {'compiler.js': stat.S_IFLNK | 0o777})
            with self.assertRaises(RuntimeError): verify_zip(path, files)
            write_zip(path, files)
            with zipfile.ZipFile(path, 'a') as z: z.writestr('compiler.js', files['compiler.js'])
            with self.assertRaises(RuntimeError): verify_zip(path, files)
            write_zip(path, files)
            path.write_bytes(path.read_bytes().replace(files['compiler.js'], b'CHANGED-COMPILER-DATA'))
            with self.assertRaises(zipfile.BadZipFile): verify_zip(path, files)


class PublicationTests(unittest.TestCase):
    def fixture(self):
        repo = 'kkgams/plugin.pack'; tag = 'v0.1.0'; expected = {'plugin.pack.wasm': b'complete'}
        release = {'id': 1, 'tag_name': tag, 'draft': False, 'prerelease': False, 'immutable': True, 'published_at': 'date', 'assets': [{'id': 2, 'name': 'plugin.pack.wasm', 'size': 8, 'state': 'uploaded', 'browser_download_url': f'https://github.com/{repo}/releases/download/{tag}/plugin.pack.wasm'}]}
        repository = {'private': False, 'visibility': 'public'}
        return repo, tag, expected, release, repository

    def test_public_complete_stable_bytes_and_negatives(self):
        repo, tag, expected, release, repository = self.fixture()
        def get(url):
            if '/download/' in url: return expected['plugin.pack.wasm']
            return json.dumps(release if '/releases/' in url else repository).encode()
        verify_public(repo, tag, expected, get)
        release['assets'][0]['download_count'] = 0
        def counted_download(url):
            if '/download/' in url:
                release['assets'][0]['download_count'] += 1
            return get(url)
        verify_public(repo, tag, expected, counted_download)
        for key in ('draft', 'prerelease', 'immutable'):
            old = release[key]; release[key] = not old
            with self.subTest(key=key), self.assertRaises(RuntimeError): verify_public(repo, tag, expected, get)
            release[key] = old
        repository['private'] = True
        with self.assertRaises(RuntimeError): verify_public(repo, tag, expected, get)
        repository['private'] = False
        with self.assertRaises(RuntimeError): verify_public(repo, tag, expected, lambda url: b'wrong' if '/download/' in url else get(url))
        release['assets'].append(copy.deepcopy(release['assets'][0]))
        with self.assertRaises(RuntimeError): verify_public(repo, tag, expected, get)
        release['assets'].pop()
        reads = 0
        def unstable(url):
            nonlocal reads
            if '/releases/tags/' in url:
                reads += 1
                if reads == 2: release['id'] = 9
            return get(url)
        with self.assertRaises(RuntimeError): verify_public(repo, tag, expected, unstable)

    def test_publication_never_creates_on_policy_or_existing_release_failure(self):
        from publication import publish
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'component.json').write_text(json.dumps({'name': 'plugin.pack'}))
            (root / 'version.txt').write_text('0.1.0')
            with patch.dict('os.environ', {'GITHUB_REPOSITORY': 'kkgams/plugin.pack', 'GITHUB_REF_NAME': 'v0.1.0'}):
                with patch('publication.api', side_effect=RuntimeError('policy GET denied')), patch('publication.subprocess.run') as run:
                    with self.assertRaises(RuntimeError): publish(root)
                    run.assert_not_called()
                with patch('publication.api', side_effect=[{'private': False, 'visibility': 'public'}, {'enabled': True, 'enforced_by_owner': False}]), patch('publication.subprocess.run', side_effect=RuntimeError('release exists')) as run:
                    with self.assertRaises(RuntimeError): publish(root)
                    self.assertEqual(run.call_count, 1)
                    self.assertEqual(run.call_args.args[0], ['bash', 'scripts/check-release-absent.sh'])

    def test_draft_first_complete_download_before_lock(self):
        from publication import publish
        repo, tag, expected, release, repository = self.fixture()
        release['draft'] = True; release['immutable'] = False
        events = []
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / 'dist').mkdir()
            (root / 'component.json').write_text(json.dumps({'name': 'plugin.pack'}))
            (root / 'version.txt').write_text('0.1.0')
            for name, data in expected.items(): (root / 'dist' / name).write_bytes(data)
            def fake_api(path, method='GET', **fields):
                events.append((method, path))
                if path.endswith('/immutable-releases'): return {'enabled': True, 'enforced_by_owner': False}
                if path.endswith('/releases/1'): return release
                return repository
            def fake_run(args, **kwargs):
                events.append(('command', args))
                if args[:3] == ['gh', 'release', 'download']:
                    for name, data in expected.items(): (Path(args[args.index('--dir') + 1]) / name).write_bytes(data)
            with patch.dict('os.environ', {'GITHUB_REPOSITORY': repo, 'GITHUB_REF_NAME': tag}), patch('publication.api', side_effect=fake_api), patch('publication.subprocess.run', side_effect=fake_run), patch('publication.subprocess.check_output', return_value=json.dumps([[release]]).encode()), patch('publication.verify_public') as verify:
                publish(root)
                verify.assert_called_once_with(repo, tag, expected)
            create = next(args for kind, args in events if kind == 'command' and args[:3] == ['gh', 'release', 'create'])
            self.assertIn('--draft', create)
            self.assertNotIn('--clobber', create)
            self.assertLess(next(i for i, e in enumerate(events) if e[0] == 'command' and e[1][:3] == ['gh', 'release', 'download']), next(i for i, e in enumerate(events) if e[0] == 'PATCH'))
            self.assertEqual(events[1], ('GET', f'repos/{repo}/immutable-releases'))

    def test_official_policy_fail_closed(self):
        repository = {'private': False, 'visibility': 'public'}
        policy(repository, {'enabled': True, 'enforced_by_owner': False})
        with self.assertRaises(RuntimeError): policy(repository, {'enabled': False, 'enforced_by_owner': False})
        with patch('publication.subprocess.check_output', side_effect=RuntimeError('403')):
            with self.assertRaises(RuntimeError): api('repos/kkgams/plugin.pack/immutable-releases')


if __name__ == '__main__':
    unittest.main()
