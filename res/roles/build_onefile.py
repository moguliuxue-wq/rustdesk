"""Build and verify an attended one-file Windows role from a verified bundle."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', choices=('controller', 'agent'), required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if os.name != 'nt':
        raise RuntimeError('Build and extraction checks require Windows')

    root = Path(__file__).resolve().parents[2]
    bundle = args.bundle.resolve()
    manifest = json.loads((bundle / 'build-manifest.json').read_text(encoding='utf-8'))
    if manifest['role'] != args.role or manifest['version'] != '1.5.1':
        raise RuntimeError('The input bundle is not the requested role and version')
    for name, expected in manifest['sha256'].items():
        path = bundle / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Input bundle changed after verification: {name}')

    title = args.role.title()
    app = bundle / f'RustDesk{title}.exe'
    if not app.is_file():
        raise RuntimeError(f'Missing compiled role EXE: {app}')
    packer = root / 'libs/portable'
    subprocess.run([sys.executable, str(packer / 'generate.py'),
                    '-f', str(bundle), '-o', str(packer), '-e', str(app), '-l', '9'],
                   cwd=root, check=True)

    source = root / 'target/release/rustdesk-portable-packer.exe'
    if not source.is_file() or source.stat().st_size < 10_000_000:
        raise RuntimeError('Native self-extracting EXE is missing or too small')
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output / f'RustDesk-1.5.1-{title}-windows-x64-portable.exe'
    shutil.copy2(source, output)
    if output.read_bytes()[:2] != b'MZ':
        raise RuntimeError('Portable output is not a Windows EXE')

    # The wrapper exits after spawning the extracted application. Verify the
    # extraction separately; a zero wrapper exit code alone is insufficient.
    subprocess.run([str(output), '--version'], cwd=args.output, check=True,
                   timeout=90, capture_output=True)
    extracted = Path(os.environ['LOCALAPPDATA']) / f'rustdesk{args.role}'
    for name in (f'RustDesk{title}.exe', 'librustdesk.dll',
                 'flutter_windows.dll', 'data/icudtl.dat',
                 'data/app.so', 'data/flutter_assets'):
        if not (extracted / name).exists():
            raise RuntimeError(f'One-file extraction is incomplete: {name}')
    with os.add_dll_directory(str(extracted)):
        dll = ctypes.CDLL(str(extracted / 'librustdesk.dll'))
        dll.rustdesk_build_role.restype = ctypes.c_uint32
        if dll.rustdesk_build_role() != {'controller': 1, 'agent': 2}[args.role]:
            raise RuntimeError('Extracted DLL has the wrong compiled role')

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.exe.sha256').write_text(
        f'{digest}  {output.name}\n', encoding='utf-8')
    print(f'Verified native one-file {args.role}: {output} ({digest})')


if __name__ == '__main__':
    main()
