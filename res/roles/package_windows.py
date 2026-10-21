"""Verify the compiled DLL identity and executable, then archive the complete bundle."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def stage_licenses(bundle, role, revision):
    root = Path(__file__).resolve().parents[2]
    sources = {'LICENCE': root / 'LICENCE',
               'licenses/enigo-LICENSE.txt': root / 'libs/enigo/LICENSE'}
    if role == 'agent':
        sources['MinHook-LICENSE.txt'] = (
            root / 'flutter/windows/runner/vendor/minhook-1.3.4/LICENSE.txt')
    installed = os.environ.get('VCPKG_INSTALLED_ROOT')
    if not installed:
        if not os.environ.get('VCPKG_ROOT'):
            raise RuntimeError('VCPKG_ROOT or VCPKG_INSTALLED_ROOT is required for licenses')
        installed = Path(os.environ['VCPKG_ROOT']) / 'installed'
    # Match the native libraries linked by the Windows x64 role workflow.
    share = Path(installed) / 'x64-windows-static/share'
    native_licenses = set(share.glob('*/copyright'))
    native_licenses.update(share / name / 'copyright' for name in (
        'aom', 'ffmpeg', 'libjpeg-turbo', 'libvpx', 'libyuv', 'mfx-dispatch', 'opus'))
    for source in sorted(native_licenses):
        sources[f'licenses/vcpkg/{source.parent.name}/copyright'] = source
    notices = bundle / 'data/flutter_assets/NOTICES.Z'
    if not notices.is_file() or not notices.stat().st_size:
        raise RuntimeError('Flutter license notices missing or empty')
    for source in sources.values():
        if not source.is_file() or not source.stat().st_size:
            raise RuntimeError(f'License file missing or empty: {source}')
    for name, source in sources.items():
        target = bundle / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (bundle / 'NOTICE.txt').write_text(
        'RustDesk upstream copyright notice:\n'
        'Copyright © 2026 Purslane Tech Pte. Ltd. All rights reserved.\n'
        f'This is a modified RustDesk 1.5.1 {role.title()} build.\n'
        'RustDesk license: GNU Affero General Public License v3; see LICENCE.\n'
        f'Source revision: https://github.com/moguliuxue-wq/rustdesk/tree/{revision}\n'
        'Build instructions: docs/windows-roles.md in that source revision.\n'
        'Third-party license and copyright notices: licenses/ and, for Agent,\n'
        'MinHook-LICENSE.txt. Flutter notices remain in data/flutter_assets/NOTICES.Z\n'
        '(gzip-compressed text). These materials also travel inside the portable EXE\n'
        f'and are extracted to %LOCALAPPDATA%/rustdesk{role}/.\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', required=True, choices=['controller', 'agent'])
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if os.name != 'nt':
        raise RuntimeError('The runtime verification must execute on Windows')
    bundle = args.bundle.resolve()
    required = ['rustdesk.exe', 'librustdesk.dll', 'flutter_windows.dll',
                'data/icudtl.dat', 'data/app.so', 'data/flutter_assets']
    for name in required:
        if not (bundle / name).exists():
            raise RuntimeError(f'Missing bundle dependency: {name}')
    with os.add_dll_directory(str(bundle)):
        dll = ctypes.CDLL(str(bundle / 'librustdesk.dll'))
        dll.rustdesk_build_role.restype = ctypes.c_uint32
        expected = {'controller': 1, 'agent': 2}[args.role]
        if dll.rustdesk_build_role() != expected:
            raise RuntimeError('DLL was not compiled for the requested role')
    # --version exercises the compiled EXE -> DLL entry, without opening a connection.
    result = subprocess.run([str(bundle / 'rustdesk.exe'), '--version'],
                            cwd=bundle, capture_output=True, text=True, timeout=30,
                            check=True)
    if result.stdout.strip() != '1.5.1':
        raise RuntimeError(f'Unexpected executable version: {result.stdout!r}')
    role_name = args.role.title()
    # Rename only AFTER proving that the native library contains the correct role.
    (bundle / 'rustdesk.exe').rename(bundle / f'RustDesk{role_name}.exe')
    # Exercise Flutter/plugin initialization too. This is a launch smoke test,
    # not a substitute for a consent/disconnect test with a real second desktop.
    process = subprocess.Popen([str(bundle / f'RustDesk{role_name}.exe')], cwd=bundle)
    try:
        try:
            code = process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        else:
            raise RuntimeError(f'GUI exited during launch smoke test: {code}')
    finally:
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       capture_output=True, check=False)
    (bundle / 'README.txt').write_text(
        f'RustDesk 1.5.1 {role_name} (Windows x64, unsigned portable bundle)\n'
        f'Extract the entire ZIP and launch RustDesk{role_name}.exe.\n'
        'Keep all DLLs and the data directory beside the EXE.\n'
        'Microsoft Visual C++ 2015-2022 x64 Runtime may be required.\n'
        'Agent requires local click approval by default. The device owner may opt in\n'
        'on the Agent home screen with a new local password (12+ characters); then\n'
        'that password can authorize later sessions without a click.\n'
        'Use the visible connection manager Disconnect button or close its window to end sessions.\n'
        'Installation, privacy screen, input blocking,\n'
        'remote elevation, terminal and TCP tunnels are disabled in Agent.\n', encoding='utf-8')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    stage_licenses(bundle, args.role, revision)
    files = {p.relative_to(bundle).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(bundle.rglob('*')) if p.is_file()}
    manifest = {'version': '1.5.1', 'role': args.role, 'commit': revision,
                'verification': ['DLL role export', 'EXE --version', '10 second GUI launch'],
                'interactive_session_tested': False, 'sha256': files}
    (bundle / 'build-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / f'RustDesk-1.5.1-{role_name}-windows-x64'
    archive = Path(shutil.make_archive(str(target), 'zip', bundle))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    print(f'Verified and archived {archive}: {digest}')


if __name__ == '__main__':
    main()
