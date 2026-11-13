import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

import jiakao as j
import merge_bank as m


def record(qid='q-one'):
    return {'id': qid, 'stem': '遇到此情形应该怎样处理？', 'kind': 'single',
            'options': {'A': '停车', 'B': '加速'}, 'answers': ['A'],
            'subjects': ['subject1'], 'images': [], 'missing_media_identity': None,
            'explanation': '', 'explanation_variants': [], 'law_variants': [],
            'provenance': [{'source_id': qid}], 'issues': ['missing_explanation']}


class MergeTests(unittest.TestCase):
    def test_option_permutation_uses_answer_text(self):
        a, b = record(), record('q-two')
        b.update(options={'A': '加速', 'B': '停车'}, answers=['B'])
        self.assertEqual(m.signature(a), m.signature(b))

    def test_answer_conflict_preserved(self):
        a, b = record(), record('q-two')
        b['answers'] = ['B']
        self.assertNotEqual(m.signature(a), m.signature(b))
        self.assertEqual(m.signature(a, False), m.signature(b, False))
        self.assertEqual(len(m.merge_records([a, b])[0]), 2)

    def test_images_and_negation_not_ignored(self):
        a, b = record(), record('q-two')
        a['images'] = [{'sha256': 'aaa'}]
        b['images'] = [{'sha256': 'bbb'}]
        self.assertNotEqual(m.signature(a), m.signature(b))
        a, b = record(), record('q-two')
        b['stem'] = b['stem'].replace('应该', '不应该')
        self.assertNotEqual(m.signature(a), m.signature(b))

    def test_distinct_missing_images_not_collapsed(self):
        a, b = record(), record('q-two')
        a['missing_media_identity'], b['missing_media_identity'] = 'url1', 'url2'
        self.assertEqual(len(m.merge_records([a, b])[0]), 2)

    def test_repeated_option_text_keeps_letter_semantics(self):
        a, b = record(), record('q-two')
        a['options'] = b['options'] = {'A': '停车', 'B': '停车'}
        b['answers'] = ['B']
        self.assertNotEqual(m.signature(a), m.signature(b))

    def test_cross_subject_merge_preserves_provenance_and_fills_explain(self):
        a, b = record(), record('q-two')
        b.update(subjects=['subject3_safe'], explanation='原来源解析',
                 explanation_variants=[{'text': '原来源解析', 'source_id': 'q-two'}])
        merged, skipped = m.merge_records([a, b])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['subjects'], ['subject1', 'subject3_safe'])
        self.assertEqual(len(merged[0]['provenance']), 2)
        self.assertEqual(merged[0]['explanation'], '原来源解析')
        self.assertNotIn('missing_explanation', merged[0]['issues'])
        self.assertTrue(skipped[0]['cross_subject'])

    def test_bad_index_and_letter_rejected(self):
        raw = {'id': 'test', 'question': '题干', 'type': 'single', 'options': ['a', 'b'],
               'answer': 0, 'answer_letter': 'B'}
        with self.assertRaises(j.ValidationError):
            m.validate_raw(raw, 'subject1')
        raw.update(answer=5, answer_letter='F')
        with self.assertRaises(j.ValidationError):
            m.validate_raw(raw, 'subject1')

    def test_inspected_wording_pair_still_checks_options(self):
        a, b = record(), record('q-two')
        a['stem'], b['stem'] = m.WORDING_PAIRS[0]
        self.assertEqual(m.signature(a), m.signature(b))
        b['answers'] = ['B']
        self.assertNotEqual(m.signature(a), m.signature(b))

    def test_supplied_archive_end_to_end(self):
        archive = j.ROOT / '驾考题库数据包(2).zip'
        if not archive.is_file():
            self.skipTest('用户数据包不随公开仓库分发')
        with tempfile.TemporaryDirectory(prefix='.test-tmp-', dir=j.ROOT) as temp:
            root = Path(temp)
            for folder in ('data', 'assets', 'docs'):
                shutil.copytree(j.ROOT / folder, root / folder)
            before = (root / 'data/questions.json').read_bytes()
            stats = m.run(archive, root)
            self.assertEqual(stats['input_questions'], 3948)
            self.assertEqual(stats['new_unique_questions'], 3761)
            self.assertEqual(stats['skipped_duplicate_records'], 187)
            self.assertEqual(stats['inspected_wording_merges'], 3)
            self.assertEqual(stats['combined_unique_questions'], 3765)
            self.assertEqual(before, (root / 'data/questions.json').read_bytes())
            records = j.read_json(root / 'local-bank/questions.json')
            self.assertEqual(len({q['id'] for q in records}), len(records))
            # Every source record survives as exactly one provenance occurrence.
            provenance = [p for q in records for p in q['provenance'] if p['source'].startswith('user-zip')]
            self.assertEqual(len(provenance), 3948)
            self.assertEqual(len({(p['source'], p['source_id']) for p in provenance}), 3948)
            self.assertTrue(all(q['vehicles'] == [] and q['rights_status'] == 'unknown'
                                for q in records if q['origin'] == 'source_question'))
            for q in records:
                for image in q['images']:
                    self.assertEqual(m.digest((root / 'local-bank' / image['path']).read_bytes()), image['sha256'])
            first = (root / 'local-bank/questions.json').read_bytes()
            self.assertEqual(m.run(archive, root), stats)
            self.assertEqual(first, (root / 'local-bank/questions.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
