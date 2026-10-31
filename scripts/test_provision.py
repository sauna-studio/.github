"""Regression tests for GitHub bootstrap safeguards. No network or credentials used."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('provision', Path(__file__).resolve().parents[1] / 'bootstrap/provision.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ProvisionTests(unittest.TestCase):
    def setUp(self):
        self.item = {'key': 'TEST-001', 'repo': '.github', 'title': 'Fixture', 'body': 'Fixture requirement',
                     'acceptance': ['First criterion', 'Second criterion'], 'dependencies': [], 'area': 'github', 'phase': 'Foundation'}
        self.state = {'issues': {}}

    def test_project_existing_item_is_reused_without_mutation(self):
        item = {'id': 'PVTI_fixture'}
        with patch.object(p, 'gh') as gh:
            self.assertEqual(p.project_item('1', 'https://github.com/sauna-studio/.github/issues/1', {'https://github.com/sauna-studio/.github/issues/1': item}), item)
            gh.assert_not_called()

    def test_project_duplicate_response_recovers_existing_item(self):
        url = 'https://github.com/sauna-studio/.github/issues/1'
        item = {'id': 'PVTI_fixture', 'content': {'url': url}}
        with patch.object(p, 'gh', side_effect=[RuntimeError('Content already exists in this project'), {'items': [item]}]) as gh:
            self.assertEqual(p.project_item('1', url, {}), item)
            self.assertEqual(gh.call_count, 2)

    def test_project_unrelated_error_is_not_hidden(self):
        with patch.object(p, 'gh', side_effect=RuntimeError('permission denied')), self.assertRaises(RuntimeError):
            p.project_item('1', 'url', {})

    def test_invalid_backlogs_fail_before_mutation(self):
        a = copy.deepcopy(self.item)
        for data in [[a, a], [dict(a, repo='outside-organization')], [dict(a, dependencies=['MISSING'])],
                     [dict(a, parent=a['key'])], [dict(a, acceptance=[])]]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                p.validate_backlog(data)
        b = dict(a, key='TEST-002', dependencies=[a['key']])
        with self.assertRaises(ValueError):
            p.validate_backlog([dict(a, dependencies=[b['key']]), b])

    def run_issues(self, existing=None, concurrent_edit=False):
        calls = []
        created_body = None
        def api(path, method='GET', data=None):
            nonlocal created_body
            calls.append((method, path, data))
            if method == 'POST':
                created_body = data['body']
                return {'number': 1, 'id': 100, 'html_url': 'https://github.com/sauna-studio/.github/issues/1', 'node_id': 'I_fixture'}
            if method == 'GET':
                return {'body': created_body + ('\nHuman note' if concurrent_edit else '')}
            return {}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bootstrap').mkdir()
            (root / 'bootstrap/backlog.json').write_text(json.dumps({'issues': [self.item]}))
            with patch.object(p, 'ROOT', root), patch.object(p, 'save'), patch.object(p, 'api', api), patch.object(p, 'pages', return_value=existing or []):
                p.issues(self.state)
        return calls

    def test_rerun_preserves_existing_human_body(self):
        old = {'title': '[TEST-001] Fixture', 'body': '<!-- sauna-backlog:TEST-001 -->\nHuman edits', 'number': 1, 'id': 100,
               'html_url': 'https://github.com/sauna-studio/.github/issues/1', 'node_id': 'I_fixture'}
        self.assertEqual(self.run_issues([old]), [])

    def test_title_only_match_fails_without_adopting_issue(self):
        with self.assertRaises(RuntimeError):
            self.run_issues([{'title': '[TEST-001] Fixture', 'body': 'Unmanaged human text'}])
        self.assertEqual(self.state['issues'], {})

    def test_same_run_concurrent_edit_is_preserved(self):
        calls = self.run_issues(concurrent_edit=True)
        self.assertEqual([c[0] for c in calls], ['POST', 'GET'])

    def test_untouched_new_issue_receives_resolved_links(self):
        calls = self.run_issues()
        self.assertEqual([c[0] for c in calls], ['POST', 'GET', 'PATCH'])


if __name__ == '__main__':
    unittest.main()
