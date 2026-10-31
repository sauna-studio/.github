"""Safety regressions for native graph synchronization; no external writes."""
import importlib.util
import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

bootstrap = Path(__file__).resolve().parents[1] / 'bootstrap'
sys.path.insert(0, str(bootstrap))
spec = importlib.util.spec_from_file_location('sync_graph', bootstrap / 'sync_graph.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.pid = 'PVT_expected'
        self.fields = [
            {'id': 'F_phase', 'name': 'Phase', 'options': [{'id': 'O_phase', 'name': 'MVP'}]},
            {'id': 'F_area', 'name': 'Area', 'options': [{'id': 'O_area', 'name': 'api'}]},
            {'id': 'F_priority', 'name': 'Priority', 'options': [
                {'id': 'O_p0', 'name': 'P0'}, {'id': 'O_p1', 'name': 'P1'}]},
            {'id': 'F_status', 'name': 'Status', 'options': [
                {'id': 'O_todo', 'name': 'Todo'}, {'id': 'O_done', 'name': 'Done'}]},
        ]

    def fixture(self, status, state='OPEN', key='MVP-001'):
        issue_id = 'I_' + key
        url = 'https://github.com/sauna-studio/sauna-api/issues/5'
        backlog = [{'key': key, 'dependencies': [], 'phase': 'MVP', 'area': 'api'}]
        indexed = {key: {'node_id': issue_id, 'url': url}}
        pi = {'id': 'PVTI_' + key, 'project': {'id': self.pid}, 'isArchived': False, 'status': status}
        nodes = {issue_id: {'id': issue_id, 'url': url, 'state': state, 'parent': None,
                            'blockedBy': {'nodes': []}, 'projectItems': {'nodes': [pi]}}}
        return backlog, indexed, nodes, pi

    def metadata(self, fixture, added=()):
        backlog, indexed, nodes, _ = fixture
        return g.metadata_operations(backlog, indexed, nodes, self.pid, self.fields, set(added))

    def status_updates(self, operations):
        return [op for op in operations if 'fieldId:"F_status"' in op]

    def test_issue_node_membership_is_used_instead_of_delayed_index(self):
        item = {'id': 'PVTI_example', 'project': {'id': 'PVT_expected'}, 'isArchived': False}
        node = {'projectItems': {'nodes': [item]}}
        self.assertEqual(g.project_item(node, 'PVT_expected'), item)
        self.assertIsNone(g.project_item(node, 'PVT_other'))

    def test_archived_and_ambiguous_membership_is_rejected(self):
        item = {'id': 'PVTI_example', 'project': {'id': 'PVT_expected'}, 'isArchived': True}
        with self.assertRaises(ValueError):
            g.project_item({'projectItems': {'nodes': [item]}}, 'PVT_expected')
        item['isArchived'] = False
        with self.assertRaises(ValueError):
            g.project_item({'projectItems': {'nodes': [item, item]}}, 'PVT_expected')

    def test_missing_node_fails(self):
        with patch.object(g, 'graphql', return_value={'nodes': [None]}), self.assertRaises(ValueError):
            g.snapshot(['missing'])

    def test_incomplete_paginated_snapshot_fails(self):
        n = {'id': 'I_example', 'blockedBy': {'pageInfo': {'hasNextPage': True}}, 'projectItems': {'pageInfo': {'hasNextPage': False}}}
        with patch.object(g, 'graphql', return_value={'nodes': [n]}), self.assertRaises(ValueError):
            g.snapshot(['I_example'])

    def test_snapshot_reads_status_directly_without_field_value_pagination(self):
        node = {'id': 'I_example', 'blockedBy': {'pageInfo': {'hasNextPage': False}},
                'projectItems': {'nodes': [], 'pageInfo': {'hasNextPage': False}}}
        with patch.object(g, 'graphql', return_value={'nodes': [node]}) as query:
            self.assertEqual(g.snapshot(['I_example']), {'I_example': node})
        self.assertIn('fieldValueByName(name:"Status")', query.call_args.args[0])
        self.assertIn('optionId', query.call_args.args[0])

    def test_existing_standard_custom_and_closed_statuses_are_preserved(self):
        for status in ['In Progress', 'Blocked', 'Done', 'Todo', 'Custom review queue']:
            for state in ['OPEN', 'CLOSED']:
                with self.subTest(status=status, state=state):
                    fixture = self.fixture({'optionId': status}, state)
                    before = deepcopy(fixture[2])
                    operations = self.metadata(fixture)
                    self.assertEqual(self.status_updates(operations), [])
                    self.assertEqual(len(operations), 3)  # Canonical planning fields still synchronize.
                    self.assertEqual(fixture[2], before)

    def test_unset_open_status_uses_todo_without_mvp001_special_case(self):
        for key in ['MVP-001', 'MVP-002', 'FOUND-001']:
            fixture = self.fixture(None, key=key)
            for added in [(), (fixture[3]['id'],)]:
                with self.subTest(key=key, added=bool(added)):
                    updates = self.status_updates(self.metadata(fixture, added))
                    self.assertEqual(len(updates), 1)
                    self.assertIn('singleSelectOptionId:"O_todo"', updates[0])

    def test_existing_closed_unset_status_is_not_changed(self):
        self.assertEqual(self.status_updates(self.metadata(self.fixture(None, state='CLOSED'))), [])

    def test_new_closed_unset_item_is_initialized_to_done(self):
        fixture = self.fixture(None, state='CLOSED')
        updates = self.status_updates(self.metadata(fixture, [fixture[3]['id']]))
        self.assertEqual(len(updates), 1)
        self.assertIn('singleSelectOptionId:"O_done"', updates[0])

    def test_status_set_after_item_creation_is_preserved(self):
        fixture = self.fixture({'optionId': 'O_blocked'})
        self.assertEqual(self.status_updates(self.metadata(fixture, [fixture[3]['id']])), [])

    def test_missing_status_projection_fails_instead_of_overwriting_unknown_progress(self):
        fixture = self.fixture(None)
        del fixture[3]['status']
        with self.assertRaisesRegex(ValueError, 'Status was not read'):
            self.metadata(fixture)

    def test_rerun_only_repairs_missing_edges_without_resetting_progress(self):
        fixture = self.fixture({'optionId': 'O_in_progress'})
        backlog, indexed, nodes, _ = fixture
        second = self.fixture({'optionId': 'O_blocked'}, key='MVP-002')
        backlog.extend(second[0])
        indexed.update(second[1])
        nodes.update(second[2])
        backlog[0]['dependencies'] = ['MVP-002']
        before_statuses = {key: deepcopy(node['projectItems']) for key, node in nodes.items()}

        first_graph = g.graph_operations(backlog, indexed, nodes)
        self.assertEqual(len(first_graph), 1)
        self.assertIn('addBlockedBy', first_graph[0])
        self.assertEqual(self.status_updates(self.metadata(fixture)), [])

        nodes[indexed['MVP-001']['node_id']]['blockedBy']['nodes'].append({'id': indexed['MVP-002']['node_id']})
        self.assertEqual(g.graph_operations(backlog, indexed, nodes), [])
        self.assertEqual(self.status_updates(self.metadata(fixture)), [])
        self.assertEqual({key: node['projectItems'] for key, node in nodes.items()}, before_statuses)

    def test_apply_and_rerun_preserve_live_status_while_repairing_one_missing_edge(self):
        backlog, indexed, nodes, _ = self.fixture({'optionId': 'O_in_progress'})
        second = self.fixture({'optionId': 'O_blocked'}, key='MVP-002')
        backlog.extend(second[0])
        indexed.update(second[1])
        nodes.update(second[2])
        backlog[0]['dependencies'] = ['MVP-002']
        for number, item in enumerate(backlog, 5):
            item.update(repo='sauna-api', acceptance=['First condition', 'Second condition'])
            record = indexed[item['key']]
            record.update(repo='sauna-api', number=number,
                          url=f'https://github.com/sauna-studio/sauna-api/issues/{number}')
            nodes[record['node_id']]['url'] = record['url']
        project = {'id': self.pid, 'number': 1, 'url': 'https://github.com/orgs/sauna-studio/projects/1'}
        state = {'project': project, 'issues': indexed}
        original_progress = {key: deepcopy(node['projectItems']) for key, node in nodes.items()}
        writes = []

        def execute(operations):
            writes.extend(operations)
            for operation in operations:
                if operation.startswith('addBlockedBy'):
                    issue_id, dependency = re.search(r'issueId:"([^"]+)",blockingIssueId:"([^"]+)"', operation).groups()
                    nodes[issue_id]['blockedBy']['nodes'].append({'id': dependency})

        def gh(*args):
            if args[:2] == ('project', 'view'):
                return project
            if args[:2] == ('project', 'field-list'):
                return {'fields': self.fields}
            self.fail(f'Unexpected external operation: {args[:2]}')

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'bootstrap').mkdir()
            (root / 'bootstrap/backlog.json').write_text(json.dumps({'issues': backlog}))
            state_path = root / 'state.json'
            state_path.write_text(json.dumps(state))
            with patch.object(g, 'ROOT', root), patch.object(g.p, 'STATE_PATH', state_path), \
                 patch.object(g.p, 'gh', side_effect=gh), patch.object(g.p, 'save'), \
                 patch.object(g, 'snapshot', side_effect=lambda _: deepcopy(nodes)), \
                 patch.object(g, 'execute', side_effect=execute), \
                 patch.object(g, 'graphql', side_effect=AssertionError('No Project additions expected')), \
                 patch.object(sys, 'argv', ['sync_graph.py', '--apply']), redirect_stdout(io.StringIO()):
                g.main()
                g.main()

        self.assertEqual(sum(op.startswith('addBlockedBy') for op in writes), 1)
        self.assertEqual(self.status_updates(writes), [])
        self.assertEqual({key: node['projectItems'] for key, node in nodes.items()}, original_progress)

    def test_mutations_are_serial_bounded_batches_and_stop_on_error(self):
        with patch.object(g, 'graphql') as query:
            g.execute(['operation{clientMutationId}'] * 41)
            self.assertEqual(query.call_count, 3)
            self.assertEqual(query.call_args_list[0].args[0].count('clientMutationId'), 20)
            self.assertEqual(query.call_args_list[2].args[0].count('clientMutationId'), 1)
        with patch.object(g, 'graphql', side_effect=RuntimeError('API failure')) as query:
            with self.assertRaises(RuntimeError):
                g.execute(['operation{clientMutationId}'] * 41)
            self.assertEqual(query.call_count, 1)


if __name__ == '__main__':
    unittest.main()
