"""Deployment wording changes preserve every other approval and repository byte."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('sync_deploy_policy', Path(__file__).with_name('sync_deploy_policy.py'))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SyncDeployPolicyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.repository('source', '.github')
        self.target = self.repository('target', 'sauna-api')
        source_agents = '# Source\n\n' + sync.NEW_APPROVAL + '\n' + sync.NEW_ENVIRONMENTS + '\n\n' + sync.common.HEADING + '\n\nTracking rule.\n'
        (self.source / 'AGENTS.md').write_text(source_agents)
        (self.source / sync.common.FORM).parent.mkdir(parents=True)
        (self.source / sync.common.FORM).write_text('name: Workaround\n')
        (self.source / sync.CODING).parent.mkdir(parents=True)
        (self.source / sync.CODING).write_text(self.coding(sync.NEW_CODING))
        (self.source / 'bootstrap').mkdir()
        (self.source / 'bootstrap/initialize_repositories.py').write_text('# ' + sync.NEW_INFRA + '\n')
        self.sha = self.commit(self.source)
        self.git(self.source, 'update-ref', 'refs/remotes/origin/main', self.sha)
        self.original_agents = ('# Consumer\r\n\r\n' + sync.OLD_APPROVAL + '\r\n' + sync.OLD_ENVIRONMENTS +
                                '\r\n\r\n## Repo rules\r\nCI, reviews, secrets and local rules stay unchanged.\r\n')
        self.original_coding = self.coding(sync.OLD_CODING).replace('\n', '\r\n')
        (self.target / 'AGENTS.md').write_bytes(self.original_agents.encode())
        (self.target / sync.CODING).parent.mkdir(parents=True)
        (self.target / sync.CODING).write_bytes(self.original_coding.encode())
        self.commit(self.target)

    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()

    def repository(self, name, repo):
        path = self.root / name
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(path)], check=True)
        self.git(path, 'config', 'user.name', 'Policy Test')
        self.git(path, 'config', 'user.email', 'policy-test@example.invalid')
        self.git(path, 'remote', 'add', 'origin', f'https://github.com/sauna-studio/{repo}.git')
        (path / 'README.md').write_text('original readme\n')
        return path

    def commit(self, root):
        self.git(root, 'add', '--all')
        self.git(root, 'commit', '-qm', 'fixture')
        return self.git(root, 'rev-parse', 'HEAD')

    def coding(self, policy):
        return 'name = "coding"\ndeveloper_instructions = """\nKeep code, reviews and secrets safe.\n' + policy + '\nReturn verification.\n"""\n'

    def apply(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return sync.sync(self.source, self.target, self.sha, **kwargs)

    def test_dry_run_and_check_are_read_only(self):
        self.assertTrue(self.apply())
        self.assertTrue(self.apply(check=True))
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), self.original_agents.encode())
        self.assertEqual((self.target / sync.CODING).read_bytes(), self.original_coding.encode())
        self.assertEqual(self.git(self.target, 'status', '--porcelain'), '')

    def test_only_known_clauses_and_source_stamp_change_with_crlf_preserved(self):
        self.assertTrue(self.apply(write=True))
        expected_agents = self.original_agents.replace(sync.OLD_APPROVAL, sync.NEW_APPROVAL).replace(sync.OLD_ENVIRONMENTS, sync.NEW_ENVIRONMENTS)
        expected_agents += '\r\n' + sync.STAMP + f'`sauna-studio/.github@{self.sha}`。\r\n'
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), expected_agents.encode())
        expected_coding = self.original_coding.replace(sync.OLD_CODING, sync.NEW_CODING.replace('\n', '\r\n'))
        self.assertEqual((self.target / sync.CODING).read_bytes(), expected_coding.encode())
        self.assertIn('Domain-wide delegation・組織全体の権限・課金リソースは明示承認を得る。', expected_agents)
        self.assertIn('create billed resources, expand permissions, or merge your own PR without explicit authorization.', expected_coding)
        self.assertEqual((self.target / 'README.md').read_text(), 'original readme\n')
        self.assertFalse(self.apply(write=True))
        self.git(self.target, 'add', 'AGENTS.md', sync.CODING.as_posix())
        self.assertEqual(self.git(self.target, '-c', 'core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol', 'diff', '--cached', '--check'), '')
        self.assertFalse(self.apply(check=True))

    def test_single_line_coding_format_is_rejected_before_any_write(self):
        coding = 'name = "coding"\ndeveloper_instructions = "' + sync.OLD_CODING + '"\n'
        (self.target / sync.CODING).write_text(coding)
        self.commit(self.target)
        with self.assertRaises(ValueError):
            self.apply(write=True)
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), self.original_agents.encode())
        self.assertEqual((self.target / sync.CODING).read_text(), coding)

    def test_new_merged_source_updates_one_provenance_marker(self):
        self.apply(write=True)
        self.commit(self.target)
        (self.source / 'README.md').write_text('another merged revision\n')
        newer = self.commit(self.source)
        self.git(self.source, 'update-ref', 'refs/remotes/origin/main', newer)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(sync.sync(self.source, self.target, newer, write=True))
            self.assertFalse(sync.sync(self.source, self.target, newer, check=True))
        agents = (self.target / 'AGENTS.md').read_text()
        self.assertEqual(agents.count(sync.STAMP), 1)
        self.assertIn(newer, agents)
        self.assertNotIn(self.sha, agents)

    def test_infrastructure_changes_only_its_existing_readme_and_approval_clause(self):
        self.git(self.target, 'remote', 'set-url', 'origin', 'https://github.com/sauna-studio/sauna-infrastructure.git')
        agents = self.original_agents + '\r\n## Infra rules\r\n' + sync.OLD_INFRA + '\r\n'
        readme = 'original prefix\r\n' + sync.OLD_INFRA + '\r\noriginal suffix\r\n'
        (self.target / 'AGENTS.md').write_bytes(agents.encode())
        (self.target / 'README.md').write_bytes(readme.encode())
        self.commit(self.target)
        self.assertTrue(self.apply(write=True))
        actual = (self.target / 'AGENTS.md').read_text()
        self.assertIn(sync.NEW_INFRA, actual)
        self.assertIn('apply・課金リソース・広いIAM付与は明示承認まで実行しない。', actual)
        self.assertEqual((self.target / 'README.md').read_bytes(), readme.replace(sync.OLD_INFRA, sync.NEW_INFRA).encode())
        self.assertFalse(self.apply(write=True))

    def test_infrastructure_does_not_create_a_missing_readme(self):
        self.git(self.target, 'remote', 'set-url', 'origin', 'https://github.com/sauna-studio/sauna-infrastructure.git')
        (self.target / 'AGENTS.md').write_bytes((self.original_agents + '\r\n' + sync.OLD_INFRA + '\r\n').encode())
        self.git(self.target, 'rm', 'README.md')
        self.commit(self.target)
        self.assertTrue(self.apply(write=True))
        self.assertFalse((self.target / 'README.md').exists())

    def test_fork_without_coding_instructions_does_not_get_a_new_file(self):
        self.git(self.target, 'remote', 'set-url', 'origin', 'https://github.com/sauna-studio/postgres-nio.git')
        self.git(self.target, 'rm', sync.CODING.as_posix())
        base = self.commit(self.target)
        for branch in ['main', 'sauna-1.33.2']:
            self.git(self.target, 'update-ref', 'refs/remotes/origin/' + branch, base)
        self.git(self.target, 'checkout', '-qb', 'codex/deploy-policy')
        self.assertTrue(self.apply(write=True))
        self.assertFalse((self.target / sync.CODING).exists())
        self.assertFalse(self.apply(write=True))

    def test_postgres_main_is_rejected_by_the_shared_guard(self):
        self.git(self.target, 'remote', 'set-url', 'origin', 'https://github.com/sauna-studio/postgres-nio.git')
        with self.assertRaises(ValueError):
            self.apply(write=True)
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), self.original_agents.encode())

    def test_unknown_target_policy_is_not_rewritten(self):
        cases = [('AGENTS.md', sync.OLD_APPROVAL, 'Custom production approval policy.'),
                 ('AGENTS.md', sync.OLD_ENVIRONMENTS, 'Custom Environment policy.'),
                 (sync.CODING.as_posix(), sync.OLD_CODING, 'Custom coding policy.')]
        for filename, old, replacement in cases:
            with self.subTest(filename=filename, old=old):
                for name, content in [('AGENTS.md', self.original_agents), (sync.CODING.as_posix(), self.original_coding)]:
                    (self.target / name).write_bytes(content.encode())
                path = self.target / filename
                path.write_bytes(path.read_bytes().replace(old.encode(), replacement.encode()))
                self.commit(self.target)
                before = {name: (self.target / name).read_bytes() for name in ['AGENTS.md', sync.CODING.as_posix()]}
                with self.assertRaises(ValueError):
                    self.apply(write=True)
                self.assertEqual(before, {name: (self.target / name).read_bytes() for name in before})

    def test_old_or_unmerged_source_policy_is_rejected(self):
        old = (self.source / 'AGENTS.md').read_text().replace(sync.NEW_APPROVAL, sync.OLD_APPROVAL)
        (self.source / 'AGENTS.md').write_text(old)
        old_sha = self.commit(self.source)
        self.git(self.source, 'update-ref', 'refs/remotes/origin/main', old_sha)
        with self.assertRaises(ValueError):
            sync.sync(self.source, self.target, old_sha, write=True)
        (self.source / 'AGENTS.md').write_text(old.replace(sync.OLD_APPROVAL, sync.NEW_APPROVAL))
        unmerged = self.commit(self.source)
        with self.assertRaises(ValueError):
            sync.sync(self.source, self.target, unmerged, write=True)
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), self.original_agents.encode())

    def test_dirty_changes_are_not_overwritten_even_after_completed_sync(self):
        (self.target / 'README.md').write_text('user change\n')
        with self.assertRaises(ValueError):
            self.apply(write=True)
        self.git(self.target, 'restore', 'README.md')
        self.apply(write=True)
        (self.target / 'README.md').write_text('another user change\n')
        with self.assertRaises(ValueError):
            self.apply(write=True)
        self.assertEqual((self.target / 'README.md').read_text(), 'another user change\n')

    def test_symlinked_coding_parent_is_rejected_before_any_write(self):
        external = self.root / 'outside'
        external.mkdir()
        self.git(self.target, 'rm', '-r', '.codex')
        (self.target / '.codex').symlink_to(external, target_is_directory=True)
        self.commit(self.target)
        with self.assertRaises(ValueError):
            self.apply(write=True)
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), self.original_agents.encode())
        self.assertEqual(list(external.iterdir()), [])

    def test_concurrent_edit_is_not_overwritten(self):
        original_updates = sync.updates
        def edited(*args, **kwargs):
            result = original_updates(*args, **kwargs)
            (self.target / sync.CODING).write_text('concurrent edit\n')
            return result
        with patch.object(sync, 'updates', side_effect=edited), self.assertRaises(ValueError):
            self.apply(write=True)
        self.assertEqual((self.target / sync.CODING).read_text(), 'concurrent edit\n')
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), self.original_agents.encode())

    def test_cli_check_reports_drift_and_then_success(self):
        scripts = self.source / 'scripts'
        scripts.mkdir()
        for module in [sync, sync.common]:
            (scripts / Path(module.__file__).name).write_bytes(Path(module.__file__).read_bytes())
        args = [sys.executable, str(scripts / 'sync_deploy_policy.py'), str(self.target), '--source-commit', self.sha]
        self.assertEqual(subprocess.run([*args, '--check'], capture_output=True).returncode, 1)
        written = subprocess.run([*args, '--write'], capture_output=True)
        self.assertEqual(written.returncode, 0, written.stderr.decode())
        checked = subprocess.run([*args, '--check'], capture_output=True)
        self.assertEqual(checked.returncode, 0, checked.stderr.decode())


if __name__ == '__main__':
    unittest.main()
