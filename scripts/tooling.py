"""Source-derived Markov tooling manifest and strict independent ZIP verification."""
import stat
from pathlib import PurePosixPath
import zipfile
from legal import legal_files
from inputs import verify_inputs

PATHS = ('packages/util/markov-junior', 'script', 'examples/demo/ng/markov',
         'plugins/markov-junior.comp/compiler', 'plugins/markov-junior.comp/test',
         'plugins/markov-junior.comp/docs')


def payload(root):
    verify_inputs(root)
    files = {}
    for directory in PATHS:
        for p in sorted((root / directory).rglob('*')):
            if p.is_file():
                files[p.relative_to(root).as_posix()] = p.read_bytes()
    for name in legal_files(root) + ['README.md']:
        files[name] = (root / name).read_bytes()
    files['package.json'] = b'{"private":true,"type":"module"}\n'
    return files


def verify_zip(path, expected):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise RuntimeError('ZIP member set differs from reviewed source')
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename or path.as_posix() != info.filename:
                raise RuntimeError(f'unsafe ZIP member: {info.filename}')
            mode = info.external_attr >> 16
            if info.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG) or info.flag_bits & 1:
                raise RuntimeError(f'nonregular ZIP member: {info.filename}')
            # read checks CRC, even for a source-derived entry of the same length.
            if archive.read(info) != expected[info.filename]:
                raise RuntimeError(f'ZIP source bytes differ: {info.filename}')
