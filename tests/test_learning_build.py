import json
from pathlib import Path
import shutil
import tempfile
import unittest

import build_learning as b
import jiakao as j


class LearningBuildTests(unittest.TestCase):
    def test_public_build_only_uses_cleared_complete_questions(self):
        with tempfile.TemporaryDirectory(prefix='.test-tmp-', dir=j.ROOT) as temporary:
            root=Path(temporary)
            for folder in ('data','assets','web'):
                shutil.copytree(j.ROOT/folder,root/folder)
            for name in ('LICENSE','LICENSE-CONTENT.md','NOTICE.md'):
                shutil.copyfile(j.ROOT/name,root/name)
            summary=b.build('public',root)
            self.assertEqual(summary['accepted'],4)
            self.assertEqual(summary['excluded'],0)
            self.assertEqual(summary['vehicle_unassigned'],0)
            self.assertTrue((root/'practice-site/core.mjs').is_file())
            bank=j.read_json(root/'practice-site/data/bank.json')
            for q in bank['questions']:
                for image in q['images']:
                    self.assertTrue((root/'practice-site'/image['path']).is_file())

    def test_incomplete_and_disputed_are_excluded(self):
        _catalog,qs=j.load()
        for field,value,reason in [('explanation','','missing_explanation'),('answers',[],'invalid_answers'),('review_status','disputed','answer_conflict')]:
            raw=dict(qs[0]);raw[field]=value
            result,reasons,_files=b.prepare_question(raw,j.ROOT)
            self.assertIsNone(result);self.assertIn(reason,reasons)
        raw=dict(qs[3]);raw['images']=[{'path':'not-present.jpg'}]
        self.assertIn('missing_image',b.prepare_question(raw,j.ROOT)[1])

    def test_local_bank_filters_actual_missing_items(self):
        path=j.ROOT/'local-bank/questions.json'
        if not path.exists():self.skipTest('本地候选题库不随公开仓库发布')
        accepted,excluded=0,[]
        topic_names={t['id']:t['title'] for t in j.load()[0]['topics']}
        for raw in j.read_json(path):
            q,reasons,_files=b.prepare_question(raw,j.ROOT,True,topic_names)
            if q:accepted+=1
            else:excluded.append(reasons)
        self.assertEqual(accepted,3573)
        self.assertEqual(len(excluded),192)
        self.assertEqual(sum('missing_image' in x for x in excluded),55)
        self.assertEqual(sum('missing_explanation' in x for x in excluded),137)
