import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from validate_repository import validate

ROOT = Path(__file__).resolve().parents[1]


class WorkaroundFormTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'foundation'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('.git', '__pycache__', '.venv'))
        self.form = self.root / '.github/ISSUE_TEMPLATE/workaround.yml'

    def change(self, edit):
        data = yaml.safe_load(self.form.read_text())
        edit(data)
        self.form.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))

    def test_form_cannot_silently_drop_its_label(self):
        self.change(lambda data: data.pop('labels'))
        self.assertIn('Workaround form must apply the workaround label', validate(self.root))

    def test_removal_criteria_cannot_be_optional(self):
        self.change(lambda data: data['body'][2]['validations'].update(required=False))
        self.assertIn('Workaround tracking fields must be required textareas', validate(self.root))

    def test_workaround_form_must_be_present(self):
        self.form.unlink()
        self.assertIn('Missing or empty .github/ISSUE_TEMPLATE/workaround.yml', validate(self.root))
