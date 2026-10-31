"""Regression: a fetchable blob at a discarded branch SHA is not a durable caller."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('initialize', Path(__file__).resolve().parents[1] / 'bootstrap/initialize_repositories.py')
i = importlib.util.module_from_spec(spec)
spec.loader.exec_module(i)


class WorkflowReferenceTests(unittest.TestCase):
    def test_default_branch_ancestor_and_head_are_allowed(self):
        sha = 'a' * 40
        for status in ('ahead', 'identical'):
            with patch.object(i, 'gh', return_value={'status': status, 'merge_base_commit': {'sha': sha}}):
                i.ensure_workflow_ref_is_durable(sha)

    def test_discarded_or_unmerged_reference_is_rejected(self):
        sha = 'a' * 40
        for status in ('behind', 'diverged'):
            with patch.object(i, 'gh', return_value={'status': status, 'merge_base_commit': {'sha': 'b' * 40}}), self.assertRaises(RuntimeError):
                i.ensure_workflow_ref_is_durable(sha)

    def test_missing_or_disagreeing_merge_base_is_rejected(self):
        for response in ({'status': 'ahead'}, {'status': 'identical', 'merge_base_commit': {'sha': 'b' * 40}}):
            with patch.object(i, 'gh', return_value=response), self.assertRaises(RuntimeError):
                i.ensure_workflow_ref_is_durable('a' * 40)

    def test_mutable_reference_is_rejected_before_network(self):
        with patch.object(i, 'gh') as gh, self.assertRaises(ValueError):
            i.ensure_workflow_ref_is_durable('main')
        gh.assert_not_called()


if __name__ == '__main__':
    unittest.main()
