"""Prepare an allowlisted GitHub source tree and reproducible public archives."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import zipfile

import jiakao as j

FILES = ['README.md','README.en.md','LICENSE','LICENSE-CONTENT.md','NOTICE.md','SECURITY.md',
         'CONTRIBUTING.md','CHANGELOG.md','pyproject.toml','.gitignore','jiakao.py',
         'merge_bank.py','build_learning.py','serve.mjs','start-learning.ps1','prepare_publication.py']
TREES = ['data','assets','docs','tests','web','.github','generated']
FORBIDDEN = {'local-bank','practice-site','__pycache__','.git','.env','publish-ready','release-bundles'}
SECRET_PATTERNS = [re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),
                   re.compile(r'github_pat_[A-Za-z0-9_]{40,}'),
                   re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]


def archive_tree(directory, destination):
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as z:
        for file in sorted(directory.rglob('*')):
            if file.is_file():
                info=zipfile.ZipInfo(file.relative_to(directory).as_posix(),(2026,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,file.read_bytes())


def prepare(root=j.ROOT):
    root=Path(root).resolve()
    # Rebuild from approved source data; local-bank is never an input here.
    result=j.package(root)
    output=root/'publish-ready'
    if output.exists():
        marker=output/'.publication-generated'
        if not marker.is_file() or output.resolve()!=root/'publish-ready':
            raise j.ValidationError('Refusing to replace an unmarked publication directory')
        shutil.rmtree(output)
    output.mkdir()
    for name in FILES:
        shutil.copyfile(root/name,output/name)
    for tree in TREES:
        shutil.copytree(root/tree,output/tree,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
    # Root-relative links must work in the extracted source archive.
    j.check_links(output)
    catalog,questions=j.load(output)
    j.validate(catalog,questions,output)
    if any(not j.publishable(q,catalog) for q in questions):
        raise j.ValidationError('Uncleared source data in publication tree')
    rows=[]
    for file in sorted(output.rglob('*')):
        if not file.is_file():continue
        relative=file.relative_to(output)
        if any(part in FORBIDDEN for part in relative.parts) or file.suffix.lower() in {'.pem','.key','.zip'}:
            raise j.ValidationError(f'Excluded material in public tree: {relative}')
        content=file.read_bytes()
        if len(content)>25*1024*1024:
            raise j.ValidationError(f'File exceeds browser upload limit: {relative}')
        if file.suffix.lower() in {'.md','.py','.json','.mjs','.yml','.toml','.ps1','.html','.css','.example'}:
            text=content.decode('utf-8-sig')
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):
                raise j.ValidationError(f'Potential secret in {relative}; inspect locally')
            if re.search(r'[A-Za-z]:[\\/]+Users[\\/]+',text):
                raise j.ValidationError(f'Personal absolute path in {relative}')
        rows.append({'path':relative.as_posix(),'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
    workflows=output/'.github/workflows'
    if (workflows/'pages.yml').exists() or any('actions/deploy-pages@' in f.read_text(encoding='utf-8') for f in workflows.glob('*.yml')):
        raise j.ValidationError('Active website deployment must not be included')
    version=catalog['version']
    manifest={'version':version,'checked_date':'2026-11-13','public_question_count':len(questions),
              'website_source_included':True,'website_deployment_enabled':False,
              'third_party_bank_included':False,'secret_scan':'common patterns only; not exhaustive',
              'files':rows,'browser_upload_batch_limit':100,
              'content_file_count':len(rows),'excludes':['local-bank/','practice-site/','raw user ZIP','personal progress','credentials']}
    j.write_json(output/'PUBLICATION-MANIFEST.json',manifest)
    j.write_text(output/'.publication-generated','Generated public-source tree; no external publication performed.')
    bundles=root/'release-bundles'
    bundles.mkdir(exist_ok=True)
    source=bundles/f'jiakao-source-{version}.zip'
    archive_tree(output,source)
    paths=[source]
    for archive in result['archives']:
        destination=bundles/Path(archive).name
        shutil.copyfile(archive,destination)
        paths.append(destination)
    j.write_text(bundles/'SHA256SUMS','\n'.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}' for p in paths))
    j.write_json(bundles/'PUBLICATION-MANIFEST.json',manifest)
    for file in paths:
        with zipfile.ZipFile(file) as z:
            if z.testzip():raise j.ValidationError(f'Corrupt ZIP: {file.name}')
    return {'source_directory':str(output),'archives':[str(p) for p in paths],
            'public_questions':len(questions),'source_files':len(rows)+2,
            'browser_batches':(len(rows)+2+99)//100,'pages_deployment':False}


if __name__=='__main__':
    print(json.dumps(prepare(),ensure_ascii=False,indent=2))
