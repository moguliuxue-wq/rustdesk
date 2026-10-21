import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('package_windows', ROOT / 'res/roles/package_windows.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)
spec = importlib.util.spec_from_file_location('build_onefile', ROOT / 'res/roles/build_onefile.py')
onefile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(onefile)


class BundleLicenseTests(unittest.TestCase):
    def test_both_roles_preserve_licenses_and_source_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            installed = Path(directory) / 'installed'
            for name in ('aom', 'ffmpeg', 'libjpeg-turbo', 'libvpx', 'libyuv',
                         'mfx-dispatch', 'opus', 'extra-native-dependency'):
                source = installed / 'x64-windows-static/share' / name / 'copyright'
                source.parent.mkdir(parents=True)
                source.write_bytes(f'{name} copyright and license\r\n'.encode())
            with patch.dict(os.environ, {'VCPKG_INSTALLED_ROOT': str(installed)}):
                for role in ('controller', 'agent'):
                    bundle = Path(directory) / role
                    notices = bundle / 'data/flutter_assets/NOTICES.Z'
                    notices.parent.mkdir(parents=True)
                    notices.write_bytes(b'flutter-notices')
                    package.stage_licenses(bundle, role, 'test-revision')
                    self.assertEqual((bundle / 'LICENCE').read_bytes(), (ROOT / 'LICENCE').read_bytes())
                    self.assertEqual((bundle / 'licenses/enigo-LICENSE.txt').read_bytes(),
                                     (ROOT / 'libs/enigo/LICENSE').read_bytes())
                    for source in installed.glob('*/share/*/copyright'):
                        copied = bundle / 'licenses/vcpkg' / source.parent.name / 'copyright'
                        self.assertEqual(copied.read_bytes(), source.read_bytes())
                    self.assertEqual(notices.read_bytes(), b'flutter-notices')
                    self.assertIn('/tree/test-revision', (bundle / 'NOTICE.txt').read_text(encoding='utf-8'))
                    if role == 'agent':
                        self.assertEqual((bundle / 'MinHook-LICENSE.txt').read_bytes(),
                                         (ROOT / 'flutter/windows/runner/vendor/minhook-1.3.4/LICENSE.txt').read_bytes())
                    else:
                        self.assertFalse((bundle / 'MinHook-LICENSE.txt').exists())

    def test_missing_native_license_stops_packaging(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            notices = bundle / 'data/flutter_assets/NOTICES.Z'
            notices.parent.mkdir(parents=True)
            notices.write_bytes(b'flutter-notices')
            with patch.dict(os.environ, {'VCPKG_INSTALLED_ROOT': str(bundle / 'missing-installed')}):
                with self.assertRaisesRegex(RuntimeError, 'License file missing or empty'):
                    package.stage_licenses(bundle, 'controller', 'test-revision')

    def test_portable_extraction_rejects_missing_or_changed_license(self):
        with tempfile.TemporaryDirectory() as directory:
            extracted = Path(directory)
            license_file = extracted / 'LICENCE'
            license_file.write_bytes(b'original license')
            hashes = {'LICENCE': hashlib.sha256(license_file.read_bytes()).hexdigest()}
            onefile.verify_extracted_files(extracted, hashes)
            for content in (b'changed license', None):
                if content is None:
                    license_file.unlink()
                else:
                    license_file.write_bytes(content)
                with self.assertRaisesRegex(RuntimeError, 'One-file extracted file missing or changed: LICENCE'):
                    onefile.verify_extracted_files(extracted, hashes)
