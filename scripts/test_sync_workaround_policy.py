"""Exercise the policy-only rollout against isolated local Git repositories."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('sync_workaround_policy', Path(__file__).with_name('sync_workaround_policy.py'))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SyncWorkaroundPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.repository('source', '.github')
        self.target = self.repository('target', 'sauna-api')
        self.source_agents = '# Common\n\n' + sync.HEADING + '\n\nNew rule with `workaround`.\n\n## Security\nNever share secrets.\n'
        (self.source / 'AGENTS.md').write_text(self.source_agents)
        (self.source / sync.FORM).parent.mkdir(parents=True)
        (self.source / sync.FORM).write_text('name: Workaround\nlabels: [workaround]\n')
        self.sha = self.commit(self.source)
        self.run_git(self.source, 'update-ref', 'refs/remotes/origin/main', self.sha)
        self.original = '# Consumer\r\n\r\n' + sync.HEADING + '\r\n\r\nOld rule.\r\n\r\n## Repo rules\r\nKeep this byte-for-byte.\r\n'
        (self.target / 'AGENTS.md').write_bytes(self.original.encode())
        (self.target / '.github/ISSUE_TEMPLATE').mkdir(parents=True)
        (self.target / '.github/ISSUE_TEMPLATE/bug.yml').write_text('existing bug form\n')
        self.commit(self.target)

    def run_git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()

    def repository(self, name, repo):
        root = self.root / name
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(root)], check=True)
        self.run_git(root, 'config', 'user.name', 'Policy Test')
        self.run_git(root, 'config', 'user.email', 'policy-test@example.invalid')
        self.run_git(root, 'remote', 'add', 'origin', f'https://github.com/sauna-studio/{repo}.git')
        (root / 'README.md').write_text('fixture\n')
        return root

    def commit(self, root):
        self.run_git(root, 'add', '--all')
        self.run_git(root, 'commit', '-qm', 'fixture')
        return self.run_git(root, 'rev-parse', 'HEAD')

    def apply(self, **options):
        with contextlib.redirect_stdout(io.StringIO()):
            return sync.sync(self.source, self.target, self.sha, **options)

    def test_dry_run_and_check_leave_the_checkout_untouched(self):
        self.assertTrue(self.apply())
        self.assertTrue(self.apply(check=True))
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), self.original.encode())
        self.assertFalse((self.target / sync.FORM).exists())
        self.assertEqual(self.run_git(self.target, 'status', '--porcelain'), '')

    def test_write_changes_only_policy_and_form_and_is_idempotent(self):
        self.assertTrue(self.apply(write=True))
        actual = (self.target / 'AGENTS.md').read_bytes()
        self.assertTrue(actual.startswith(b'# Consumer\r\n\r\n'))
        self.assertTrue(actual.endswith(b'## Repo rules\r\nKeep this byte-for-byte.\r\n'))
        self.assertIn(self.sha.encode(), actual)
        self.assertEqual((self.target / sync.FORM).read_bytes(), (self.source / sync.FORM).read_bytes())
        self.assertEqual((self.target / '.github/ISSUE_TEMPLATE/bug.yml').read_text(), 'existing bug form\n')
        self.assertFalse(self.apply(write=True))
        self.assertFalse(self.apply(check=True))

    def test_cli_check_reports_drift_then_success_without_rewriting(self):
        script = self.source / 'scripts/sync_workaround_policy.py'
        script.parent.mkdir()
        script.write_bytes(Path(sync.__file__).read_bytes())
        args = [sys.executable, str(script), str(self.target), '--source-commit', self.sha]
        drift = subprocess.run([*args, '--check'], capture_output=True)
        self.assertEqual(drift.returncode, 1)
        self.assertEqual(drift.stdout, b'')
        written = subprocess.run([*args, '--write'], capture_output=True)
        self.assertEqual(written.returncode, 0, written.stderr.decode())
        before = (self.target / 'AGENTS.md').read_bytes()
        clean = subprocess.run([*args, '--check'], capture_output=True)
        self.assertEqual(clean.returncode, 0, clean.stderr.decode())
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), before)

    def test_unmerged_or_mutable_source_cannot_write(self):
        for sha in ['main', 'a' * 40]:
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                sync.sync(self.source, self.target, sha, write=True)
        (self.source / 'AGENTS.md').write_text(self.source_agents.replace('New rule', 'Unmerged rule'))
        unmerged = self.commit(self.source)
        with self.assertRaises(ValueError):
            sync.sync(self.source, self.target, unmerged, write=True)
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), self.original.encode())

    def test_dirty_target_is_not_overwritten_even_after_a_successful_rollout(self):
        (self.target / 'README.md').write_text('user edit\n')
        with self.assertRaises(ValueError):
            self.apply(write=True)
        self.assertEqual((self.target / 'README.md').read_text(), 'user edit\n')
        self.run_git(self.target, 'restore', 'README.md')
        self.apply(write=True)
        (self.target / 'README.md').write_text('another user edit\n')
        with self.assertRaises(ValueError):
            self.apply(write=True)

    def test_edit_after_planning_is_not_overwritten(self):
        original_updates = sync.updates
        def editing_updates(*args, **kwargs):
            changes = original_updates(*args, **kwargs)
            (self.target / 'AGENTS.md').write_text('concurrent user edit\n')
            return changes
        with patch.object(sync, 'updates', side_effect=editing_updates), self.assertRaises(ValueError):
            self.apply(write=True)
        self.assertEqual((self.target / 'AGENTS.md').read_text(), 'concurrent user edit\n')
        self.assertFalse((self.target / sync.FORM).exists())

    def test_symlinked_policy_or_parent_is_rejected(self):
        external = self.root / 'outside'
        external.mkdir()
        outside_agents = external / 'AGENTS.md'
        outside_agents.write_text('outside content\n')
        (self.target / 'AGENTS.md').unlink()
        (self.target / 'AGENTS.md').symlink_to(outside_agents)
        self.commit(self.target)
        with self.assertRaises(ValueError):
            self.apply(write=True)
        self.assertEqual(outside_agents.read_text(), 'outside content\n')
        (self.target / 'AGENTS.md').unlink()
        (self.target / 'AGENTS.md').write_bytes(self.original.encode())
        self.run_git(self.target, 'rm', '-r', '.github')
        (self.target / '.github').symlink_to(external, target_is_directory=True)
        self.commit(self.target)
        with self.assertRaises(ValueError):
            self.apply(write=True)
        self.assertFalse((external / 'ISSUE_TEMPLATE/workaround.yml').exists())

    def test_issues_disabled_fork_can_get_explicit_minimal_instructions_only(self):
        self.target = self.repository('fork', 'postgres-nio')
        base = self.commit(self.target)
        self.run_git(self.target, 'update-ref', 'refs/remotes/origin/main', base)
        self.run_git(self.target, 'update-ref', 'refs/remotes/origin/sauna-1.33.2', base)
        self.run_git(self.target, 'checkout', '-qb', 'codex/fork-policy')
        with self.assertRaises(ValueError):
            self.apply(write=True, issues_disabled=True)
        with self.assertRaises(ValueError):
            self.apply(write=True, allow_new_agents=True)
        self.assertTrue(self.apply(write=True, issues_disabled=True, allow_new_agents=True))
        self.assertIn('New rule', (self.target / 'AGENTS.md').read_text())
        self.assertFalse((self.target / sync.FORM).exists())
        self.assertFalse(self.apply(write=True, issues_disabled=True, allow_new_agents=True))
        self.run_git(self.target, 'add', 'AGENTS.md')
        checked = subprocess.run(['git', '-C', str(self.target), 'diff', '--cached', '--check'], capture_output=True)
        self.assertEqual(checked.returncode, 0, checked.stdout.decode())
        self.assertFalse(self.apply(write=True, issues_disabled=True, allow_new_agents=True))

    def test_postgres_main_is_not_a_rollout_checkout(self):
        self.run_git(self.target, 'remote', 'set-url', 'origin', 'https://github.com/sauna-studio/postgres-nio.git')
        base = self.run_git(self.target, 'rev-parse', 'HEAD')
        self.run_git(self.target, 'update-ref', 'refs/remotes/origin/main', base)
        self.run_git(self.target, 'update-ref', 'refs/remotes/origin/sauna-1.33.2', base)
        with self.assertRaises(ValueError):
            self.apply(write=True, issues_disabled=True)
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), self.original.encode())

    def test_postgres_feature_requires_the_maintenance_history(self):
        self.run_git(self.target, 'remote', 'set-url', 'origin', 'https://github.com/sauna-studio/postgres-nio.git')
        base = self.run_git(self.target, 'rev-parse', 'HEAD')
        self.run_git(self.target, 'update-ref', 'refs/remotes/origin/main', base)
        self.run_git(self.target, 'checkout', '-qb', 'sauna-1.33.2')
        (self.target / 'README.md').write_text('maintenance branch\n')
        maintenance = self.commit(self.target)
        self.run_git(self.target, 'update-ref', 'refs/remotes/origin/sauna-1.33.2', maintenance)
        with self.assertRaises(ValueError):
            self.apply(write=True, issues_disabled=True)
        self.run_git(self.target, 'checkout', '-q', 'main')
        self.run_git(self.target, 'checkout', '-qb', 'codex/wrong-base')
        with self.assertRaises(ValueError):
            self.apply(write=True, issues_disabled=True)
        self.run_git(self.target, 'checkout', '-q', '--detach', maintenance)
        with self.assertRaises(ValueError):
            self.apply(write=True, issues_disabled=True)
        self.run_git(self.target, 'checkout', '-qb', 'codex/maintenance-policy')
        (self.target / 'README.md').write_text('feature branch change\n')
        self.commit(self.target)
        self.assertTrue(self.apply(write=True, issues_disabled=True))
        self.assertFalse(self.apply(write=True, issues_disabled=True))

    def test_postgres_merged_main_history_is_not_a_policy_rollout(self):
        self.run_git(self.target, 'remote', 'set-url', 'origin', 'https://github.com/sauna-studio/postgres-nio.git')
        base = self.run_git(self.target, 'rev-parse', 'HEAD')
        (self.target / 'README.md').write_text('main-only change\n')
        upstream = self.commit(self.target)
        self.run_git(self.target, 'update-ref', 'refs/remotes/origin/main', upstream)
        self.run_git(self.target, 'checkout', '-qb', 'sauna-1.33.2', base)
        (self.target / 'maintenance.txt').write_text('maintenance-only change\n')
        maintenance = self.commit(self.target)
        self.run_git(self.target, 'update-ref', 'refs/remotes/origin/sauna-1.33.2', maintenance)
        self.run_git(self.target, 'checkout', '-qb', 'codex/mixed-history', 'main')
        self.run_git(self.target, 'merge', '-q', '--no-ff', '-m', 'fixture merge', 'sauna-1.33.2')
        with self.assertRaises(ValueError):
            self.apply(write=True, issues_disabled=True)
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), self.original.encode())

    def test_tracking_section_at_eof_ends_with_one_newline(self):
        prefix = b'# Consumer\r\n\r\n'
        (self.target / 'AGENTS.md').write_bytes(prefix + sync.HEADING.encode() + b'\r\n\r\nOld rule.\r\n\r\n')
        self.commit(self.target)
        self.assertTrue(self.apply(write=True))
        actual = (self.target / 'AGENTS.md').read_bytes()
        self.assertTrue(actual.startswith(prefix))
        self.assertTrue(actual.endswith(b'\n'))
        self.assertFalse(actual.endswith(b'\n\n'))
        self.run_git(self.target, 'add', 'AGENTS.md', sync.FORM.as_posix())
        checked = subprocess.run(['git', '-C', str(self.target), 'diff', '--cached', '--check'], capture_output=True)
        self.assertEqual(checked.returncode, 0, checked.stdout.decode())
        self.assertFalse(self.apply(write=True))

    def test_unknown_or_duplicate_sections_are_not_guessed(self):
        for text in ['# Custom rules\n', self.original + '\n' + self.original]:
            with self.subTest(text=text):
                (self.target / 'AGENTS.md').write_bytes(text.encode())
                self.commit(self.target)
                with self.assertRaises(ValueError):
                    self.apply(write=True)
                self.assertEqual((self.target / 'AGENTS.md').read_bytes(), text.encode())


if __name__ == '__main__':
    unittest.main()
