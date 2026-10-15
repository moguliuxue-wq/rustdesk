import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('rustdesk_build', ROOT / 'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BuildSelectorTests(unittest.TestCase):
    def features(self, *argv):
        return build.get_features(build.make_parser().parse_args(list(argv)))

    def test_roles_select_distinct_native_features(self):
        for role, other in [('agent', 'controller'), ('controller', 'agent')]:
            features = self.features('--flutter', '--role', role)
            self.assertIn('flutter', features)
            self.assertIn('role-' + role, features)
            self.assertNotIn('role-' + other, features)

    def test_standard_build_stays_standard(self):
        self.assertFalse(any(f.startswith('role-') for f in self.features('--flutter')))

    def test_role_requires_flutter(self):
        with self.assertRaises(ValueError):
            self.features('--role', 'agent')

    def test_role_cannot_reuse_unknown_dll(self):
        with self.assertRaises(ValueError):
            self.features('--flutter', '--role', 'agent', '--skip-cargo')


if __name__ == '__main__':
    unittest.main()
