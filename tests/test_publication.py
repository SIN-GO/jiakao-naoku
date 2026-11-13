from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

import jiakao as j
import prepare_publication as p


class PublicationTests(unittest.TestCase):
    def test_allowlist_archives_and_disabled_website(self):
        with tempfile.TemporaryDirectory(prefix='.test-tmp-',dir=j.ROOT) as temporary:
            root=Path(temporary)
            for name in p.FILES:
                shutil.copyfile(j.ROOT/name,root/name)
            for tree in p.TREES:
                shutil.copytree(j.ROOT/tree,root/tree,ignore=shutil.ignore_patterns('__pycache__'))
            (root/'local-bank').mkdir()
            (root/'local-bank/private.json').write_text('DO-NOT-PUBLISH',encoding='utf-8')
            result=p.prepare(root)
            self.assertEqual(result['public_questions'],4)
            self.assertFalse(result['pages_deployment'])
            public=root/'publish-ready'
            self.assertFalse((public/'local-bank').exists())
            self.assertTrue((public/'README.en.md').exists())
            self.assertTrue((public/'web/core.mjs').exists())
            self.assertFalse((public/'.github/workflows/pages.yml').exists())
            manifest=j.read_json(public/'PUBLICATION-MANIFEST.json')
            self.assertFalse(manifest['third_party_bank_included'])
            j.check_links(public)
            for filename in result['archives']:
                with zipfile.ZipFile(filename) as z:
                    self.assertIsNone(z.testzip())
                    self.assertFalse(any('local-bank/' in name for name in z.namelist()))
