#!/usr/bin/env python3
"""Embed and verify exact licensing bytes in a WebAssembly component."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import os
import sys
import tempfile

COMPONENT_HEADER = b"\x00asm\x0d\x00\x01\x00"
LICENSE_SECTION = "gams.license"
NOTICE_SECTION = "gams.notice"
NOTICE_SECTIONS = frozenset((LICENSE_SECTION, NOTICE_SECTION))


class NoticeError(ValueError):
    """The component or its embedded licensing notices are invalid."""


@dataclass(frozen=True)
class Section:
    raw: bytes
    name: str | None
    contents: bytes | None


def encode_u32(value: int) -> bytes:
    if not 0 <= value <= 0xFFFFFFFF:
        raise NoticeError(f"value outside u32 range: {value}")
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            encoded.append(byte | 0x80)
        else:
            encoded.append(byte)
            return bytes(encoded)


def decode_u32(data: bytes, offset: int, context: str) -> tuple[int, int]:
    start = offset
    value = 0
    for index in range(5):
        if offset >= len(data):
            raise NoticeError(f"truncated u32 LEB for {context}")
        byte = data[offset]
        offset += 1
        if index == 4 and (byte & 0xF0):
            raise NoticeError(f"u32 LEB overflow for {context}")
        value |= (byte & 0x7F) << (index * 7)
        if not byte & 0x80:
            if data[start:offset] != encode_u32(value):
                raise NoticeError(f"non-canonical u32 LEB for {context}")
            return value, offset
    raise NoticeError(f"unterminated u32 LEB for {context}")


def parse_component(data: bytes) -> list[Section]:
    if not data:
        raise NoticeError("empty input is not a WebAssembly component")
    if len(data) < len(COMPONENT_HEADER):
        raise NoticeError("truncated WebAssembly component header")
    if data[:4] != b"\x00asm":
        raise NoticeError("invalid WebAssembly magic")
    if data[4:8] != COMPONENT_HEADER[4:]:
        if data[4:8] == b"\x01\x00\x00\x00":
            raise NoticeError("expected a WebAssembly component, got a core module")
        raise NoticeError("unsupported WebAssembly component header")

    sections = []
    offset = len(COMPONENT_HEADER)
    while offset < len(data):
        start = offset
        section_id = data[offset]
        offset += 1
        payload_size, offset = decode_u32(data, offset, "section size")
        end = offset + payload_size
        if end > len(data):
            raise NoticeError("section payload extends past end of component")
        name = None
        contents = None
        if section_id == 0:
            name_size, name_offset = decode_u32(data, offset, "custom section name size")
            name_end = name_offset + name_size
            if name_end > end:
                raise NoticeError("custom section name extends past its payload")
            try:
                name = data[name_offset:name_end].decode("utf-8")
            except UnicodeDecodeError as error:
                raise NoticeError("custom section name is not valid UTF-8") from error
            contents = data[name_end:end]
        sections.append(Section(data[start:end], name, contents))
        offset = end
    return sections


def custom_section(name: str, contents: bytes) -> bytes:
    encoded_name = name.encode("utf-8")
    payload = encode_u32(len(encoded_name)) + encoded_name + contents
    return b"\x00" + encode_u32(len(payload)) + payload


def expected_notices(license_path: Path, notice_path: Path | None) -> dict[str, bytes]:
    try:
        notices = {LICENSE_SECTION: license_path.read_bytes()}
        if notice_path is not None:
            notices[NOTICE_SECTION] = notice_path.read_bytes()
    except OSError as error:
        raise NoticeError(str(error)) from error
    for name, contents in notices.items():
        if not contents.strip():
            raise NoticeError(f"empty licensing text for {name}")
    return notices


def embed_bytes(component: bytes, notices: dict[str, bytes]) -> bytes:
    sections = parse_component(component)
    retained = (section.raw for section in sections if section.name not in NOTICE_SECTIONS)
    embedded = bytearray(COMPONENT_HEADER)
    embedded.extend(b"".join(retained))
    for name in (LICENSE_SECTION, NOTICE_SECTION):
        if name in notices:
            embedded.extend(custom_section(name, notices[name]))
    return bytes(embedded)


def verify_bytes(component: bytes, notices: dict[str, bytes]) -> None:
    sections = parse_component(component)
    found: dict[str, list[bytes]] = {name: [] for name in NOTICE_SECTIONS}
    for section in sections:
        if section.name in NOTICE_SECTIONS:
            assert section.contents is not None
            found[section.name].append(section.contents)

    for name in NOTICE_SECTIONS:
        values = found[name]
        expected = notices.get(name)
        if len(values) > 1:
            raise NoticeError(f"duplicate {name} custom sections")
        if expected is None:
            if values:
                raise NoticeError(f"unexpected {name} custom section")
        elif not values:
            raise NoticeError(f"missing {name} custom section")
        elif values[0] != expected:
            raise NoticeError(f"stale or altered {name} custom section")


def write_atomic(path: Path, contents: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as output:
            temporary_name = output.name
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_name, path)
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("embed", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("artifact", type=Path)
        subparser.add_argument("--license", required=True, type=Path)
        subparser.add_argument("--notice", type=Path)
        if command == "embed":
            subparser.add_argument("--output", type=Path,
                                   help="output path (default: replace artifact atomically)")
    args = parser.parse_args(argv)

    try:
        component = args.artifact.read_bytes()
        notices = expected_notices(args.license, args.notice)
        if args.command == "embed":
            output_path = args.output if args.output is not None else args.artifact
            embedded = embed_bytes(component, notices)
            verify_bytes(embedded, notices)
            write_atomic(output_path, embedded)
        else:
            verify_bytes(component, notices)
    except (OSError, NoticeError) as error:
        print(f"wasm-notices: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
