import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

import jiakao as j


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='.test-tmp-', dir=j.ROOT)
        self.root = Path(self.temp.name)
        for folder in ('data', 'assets', 'docs'):
            shutil.copytree(j.ROOT / folder, self.root / folder)
        for name in ('LICENSE', 'LICENSE-CONTENT.md', 'NOTICE.md'):
            shutil.copyfile(j.ROOT / name, self.root / name)
        self.catalog, self.questions = j.load(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        j.write_json(self.root / 'data/catalog.json', self.catalog)
        j.write_json(self.root / 'data/questions.json', self.questions)

    def invalid(self, change):
        change()
        with self.assertRaises(j.ValidationError):
            j.validate(self.catalog, self.questions, self.root)

    def test_all_types_and_original_samples_valid(self):
        j.validate(self.catalog, self.questions, self.root)
        self.assertEqual({q['kind'] for q in self.questions}, {'true_false', 'single', 'multiple'})
        self.assertTrue(any(q['images'] for q in self.questions))
        self.assertEqual(len(self.catalog['vehicles']), 17)

    def test_duplicate_id_rejected(self):
        self.invalid(lambda: self.questions.append(copy.deepcopy(self.questions[0])))

    def test_bad_answer_rejected(self):
        self.invalid(lambda: self.questions[0].update(answers=['Z']))

    def test_multiple_answers_required(self):
        self.invalid(lambda: self.questions[2].update(answers=['A']))

    def test_unknown_vehicle_rejected(self):
        self.invalid(lambda: self.questions[0].update(vehicles=['C99']))

    def test_source_missing_rejected(self):
        self.invalid(lambda: self.questions[0].update(sources=['not-registered']))

    def test_rights_metadata_required(self):
        self.invalid(lambda: self.catalog['sources'][0].pop('image_terms'))

    def test_review_evidence_required(self):
        self.invalid(lambda: self.questions[0].update(evidence=[]))

    def test_topic_summary_required(self):
        self.invalid(lambda: self.catalog['topics'][0].pop('summary'))

    def test_unknown_evidence_source_withheld(self):
        self.catalog['sources'][1]['redistribution'] = 'unknown'
        self.save()
        self.assertEqual(j.build(self.root)['published'], 0)

    def test_missing_image_rejected(self):
        self.invalid(lambda: self.questions[3]['images'][0].update(path='missing.svg'))

    def test_image_path_escape_rejected(self):
        self.invalid(lambda: self.questions[3]['images'][0].update(path='../README.md'))

    def test_disputed_and_uncleared_content_never_shipped(self):
        self.questions[0].update(review_status='disputed', stem='WITHHELD-SECRET-TEXT')
        self.questions[1]['rights_status'] = 'unknown'
        self.save()
        result = j.build(self.root)
        self.assertEqual(result['published'], 2)
        output = self.root / 'generated'
        for p in output.rglob('*'):
            if p.is_file():
                self.assertNotIn(b'WITHHELD-SECRET-TEXT', p.read_bytes())
        records = j.read_json(output / 'api/v1/questions.json')
        self.assertNotIn('jk-demo-001', [q['id'] for q in records])
        index = (output / 'vault/30-疑点复核/疑点清单.md').read_text(encoding='utf-8')
        self.assertIn('jk-demo-001', index)

    def test_source_and_image_permission_gate(self):
        original = self.catalog['sources'][0]
        original['redistribution'] = 'unknown'
        self.assertFalse(j.publishable(self.questions[0], self.catalog))
        original['redistribution'] = 'cleared'
        self.questions[3]['images'][0]['source_id'] = 'mps-172'
        self.assertFalse(j.publishable(self.questions[3], self.catalog))

    def test_export_note_data_match_and_local_links(self):
        j.build(self.root)
        folder = self.root / 'generated'
        records = j.read_json(folder / 'api/v1/questions.json')
        self.assertEqual(records, sorted(self.questions, key=lambda q: q['id']))
        for q in records:
            note = (folder / f"vault/10-试题/{q['id']}.md").read_text(encoding='utf-8')
            for field in ('stem', 'explanation', 'reasoning', 'pitfall', 'review_note'):
                self.assertIn(q[field], note)
            for v in q['vehicles']:
                self.assertIn(v, note)
            self.assertIn(', '.join(q['answers']), note)
            for s in q['sources']:
                self.assertIn(s, note)
        self.assertTrue((folder / 'vault/90-图片/exam-structure.svg').is_file())
        j.check_links(folder / 'vault')
        manifest = j.read_json(folder / 'api/v1/manifest.json')
        self.assertEqual(len(manifest['partitions']), 34)
        self.assertEqual(manifest['unique_questions'], 4)
        for p in manifest['partitions']:
            items = j.read_json(folder / 'api/v1' / p['path'])
            self.assertEqual(len(items), p['count'])
            self.assertTrue(all(p['vehicle'] in q['vehicles'] and p['subject'] == q['subject'] for q in items))
        self.assertEqual(j.read_json(folder / 'api/v1/vehicles/C6/subject1.json'), [])

    def test_broken_link_detected(self):
        folder = self.root / 'broken'
        folder.mkdir()
        (folder / 'index.md').write_text('[x](missing.md)', encoding='utf-8')
        with self.assertRaises(j.ValidationError):
            j.check_links(folder)

    def test_rebuild_removes_withdrawn_note(self):
        j.build(self.root)
        self.questions[0]['review_status'] = 'disputed'
        self.save()
        j.build(self.root)
        self.assertFalse((self.root / 'generated/vault/10-试题/jk-demo-001.md').exists())

    def test_output_protects_existing_directory(self):
        with self.assertRaises(j.ValidationError):
            j.build(self.root, self.root / 'data')
        self.assertTrue((self.root / 'data/questions.json').is_file())

    def test_import_is_atomic_and_duplicate_safe(self):
        before = (self.root / 'data/questions.json').read_bytes()
        incoming = self.root / 'incoming.json'
        j.write_json(incoming, [self.questions[0]])
        with self.assertRaises(j.ValidationError):
            j.import_questions(incoming, self.root)
        self.assertEqual(before, (self.root / 'data/questions.json').read_bytes())
        q = copy.deepcopy(self.questions[0])
        q.update(id='new-pending', review_status='pending')
        j.write_json(incoming, [q])
        self.assertEqual(j.import_questions(incoming, self.root)['imported'], 1)
        self.assertEqual(j.build(self.root)['published'], 4)

    def test_archives_reproducible_and_offline_usable(self):
        first = j.package(self.root)
        archives = {p: Path(p).read_bytes() for p in first['archives']}
        j.package(self.root)
        for filename, expected in archives.items():
            self.assertEqual(expected, Path(filename).read_bytes())
            with zipfile.ZipFile(filename) as archive:
                self.assertIsNone(archive.testzip())
                archive.extractall(self.root / 'unpacked')
        j.check_links(self.root / 'unpacked/vault')
        self.assertTrue((self.root / 'unpacked/vault/90-图片/exam-structure.svg').exists())
        self.assertEqual(len(j.read_json(self.root / 'unpacked/api/v1/questions.json')), 4)
        self.assertTrue((self.root / 'unpacked/api/LICENSE-CONTENT.md').exists())


if __name__ == '__main__':
    unittest.main()
