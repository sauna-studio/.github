"""Safety regressions for native graph synchronization; no external writes."""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

bootstrap = Path(__file__).resolve().parents[1] / 'bootstrap'
sys.path.insert(0, str(bootstrap))
spec = importlib.util.spec_from_file_location('sync_graph', bootstrap / 'sync_graph.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class GraphTests(unittest.TestCase):
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
