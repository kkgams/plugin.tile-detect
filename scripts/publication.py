#!/usr/bin/env python3
"""Draft-first publication with fail-closed policy and unauthenticated byte checks.
Only GITHUB_TOKEN is used. The official policy GET requires admin-read access;
if the workflow token cannot read it, publication is blocked (no extra secret).
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request


def public_get(url):
    request = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def api(path, method='GET', **fields):
    args = ['gh', 'api', '--method', method, '-H', 'X-GitHub-Api-Version: 2022-11-28', path]
    for key, value in fields.items():
        args += ['-F', f'{key}={str(value).lower() if isinstance(value, bool) else value}']
    return json.loads(subprocess.check_output(args))


def policy(repository, settings):
    if repository['private'] is not False or repository['visibility'] != 'public' or settings['enabled'] is not True:
        raise RuntimeError('Public repository and enabled immutable-release policy required')
    if not isinstance(settings['enforced_by_owner'], bool):
        raise RuntimeError('Malformed immutable-release policy')


def validate_release(release, repo, tag, expected, draft=False):
    if release['tag_name'] != tag or release['draft'] is not draft or release['prerelease'] is not False:
        raise RuntimeError('Noncanonical/draft/prerelease metadata')
    if not draft and (release['immutable'] is not True or not release['published_at']):
        raise RuntimeError('Public release is not immutable')
    assets = release['assets']
    if len(assets) != len(expected) or {a['name'] for a in assets} != set(expected):
        raise RuntimeError('Incomplete/duplicate/extra release assets')
    for asset in assets:
        name = asset['name']
        url = f'https://github.com/{repo}/releases/download/{tag}/{name}'
        if asset['state'] != 'uploaded' or asset['size'] != len(expected[name]) or asset['browser_download_url'] != url:
            raise RuntimeError('Noncanonical release asset metadata')


def stable_metadata(release):
    # Downloads legitimately increment this counter, including our own checks.
    # All other metadata, including asset IDs/types/digests/timestamps, is bound.
    return {key: [{k: v for k, v in asset.items() if k != 'download_count'} for asset in value]
            if key == 'assets' else value for key, value in release.items()}


def verify_public(repo, tag, expected, get=public_get):
    base = f'https://api.github.com/repos/{repo}'
    repository = json.loads(get(base))
    if repository['private'] is not False or repository['visibility'] != 'public':
        raise RuntimeError('Repository is not publicly readable')
    url = base + '/releases/tags/' + tag
    before = json.loads(get(url))
    validate_release(before, repo, tag, expected)
    for asset in before['assets']:
        if get(asset['browser_download_url']) != expected[asset['name']]:
            raise RuntimeError('Downloaded public asset differs from candidate')
    after = json.loads(get(url))
    validate_release(after, repo, tag, expected)
    if stable_metadata(before) != stable_metadata(after):
        raise RuntimeError('Release metadata changed during independent download')


def publish(root):
    spec = json.loads((root / 'component.json').read_text())
    repo, tag = os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_REF_NAME']
    if repo != 'kkgams/' + spec['name'] or tag != 'v' + (root / 'version.txt').read_text().strip():
        raise RuntimeError('Noncanonical publication identity')
    # No API failure is interpreted as a disabled-but-acceptable policy.
    policy(api(f'repos/{repo}'), api(f'repos/{repo}/immutable-releases'))
    subprocess.run(['bash', 'scripts/check-release-absent.sh'], cwd=root, check=True)
    expected = {p.name: p.read_bytes() for p in (root / 'dist').iterdir()}
    # create refuses preexisting tags/releases; never upload --clobber or repair.
    subprocess.run(['gh', 'release', 'create', tag, '--repo', repo, '--draft', '--verify-tag', '--latest=false',
                    '--title', spec['name'] + ' ' + tag, '--notes', 'Source-bound reviewed candidate; see README.md for coverage.',
                    *[str(root / 'dist' / name) for name in expected]], check=True)
    # The tag endpoint is for published releases. Enumerate authenticated drafts
    # with pagination instead, and demand exactly the newly reserved release.
    pages = json.loads(subprocess.check_output(['gh', 'api', '--paginate', '--slurp', f'repos/{repo}/releases?per_page=100']))
    matches = [release for page in pages for release in page if release['tag_name'] == tag]
    if len(matches) != 1:
        raise RuntimeError('Draft reservation is missing or ambiguous')
    draft = matches[0]
    validate_release(draft, repo, tag, expected, draft=True)
    # Compare authenticated staged downloads before immutable publication locks them.
    with tempfile.TemporaryDirectory() as directory:
        subprocess.run(['gh', 'release', 'download', tag, '--repo', repo, '--dir', directory], check=True)
        downloaded = {p.name: p.read_bytes() for p in Path(directory).iterdir()}
        if downloaded != expected:
            raise RuntimeError('Draft downloaded bytes differ')
    policy(api(f'repos/{repo}'), api(f'repos/{repo}/immutable-releases'))
    if stable_metadata(api(f'repos/{repo}/releases/{draft["id"]}')) != stable_metadata(draft):
        raise RuntimeError('Draft metadata changed during download; refusing publication')
    api(f'repos/{repo}/releases/{draft["id"]}', 'PATCH', draft=False, make_latest='false')
    verify_public(repo, tag, expected)
    # Exact downloaded bytes above imply the source-derived ZIP checks already
    # performed by verify-candidate apply to these final public assets too.


if __name__ == '__main__':
    publish(Path(__file__).resolve().parents[1])
