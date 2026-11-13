"""Build the static learning app; incomplete records never reach its bank."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import jiakao as j

CATEGORY_NAMES = {'operation': '驾驶操作', 'law': '法规与记分', 'signal': '交通信号与标志',
                  'safety': '安全驾驶', 'case': '情景与事故案例'}


def prepare_question(raw, root, local=False, topic_names=None):
    reasons = []
    stem = raw.get('stem', '')
    options, answers = raw.get('options', {}), raw.get('answers', [])
    if not isinstance(stem, str) or not stem.strip():
        reasons.append('missing_stem')
    valid_options = isinstance(options, dict) and len(options) >= 2 and all(isinstance(k, str) and isinstance(v, str) and v.strip() for k,v in options.items())
    if not valid_options:
        reasons.append('invalid_options')
    if (not isinstance(answers, list) or not answers or not all(isinstance(a, str) and valid_options and a in options for a in answers)
            or len(answers) != len(set(answers))):
        reasons.append('invalid_answers')
    kind = raw.get('kind')
    if kind not in {'true_false', 'single', 'multiple'}:
        reasons.append('invalid_kind')
    elif isinstance(answers, list) and (len(answers) < 2 if kind == 'multiple' else len(answers) != 1):
        reasons.append('invalid_answer_count')
    if not isinstance(raw.get('explanation'), str) or not raw['explanation'].strip():
        reasons.append('missing_explanation')
    if raw.get('review_status') == 'disputed' or 'answer_conflict' in raw.get('issues', []):
        reasons.append('answer_conflict')
    if any(x in raw.get('issues', []) for x in ('missing_image', 'possible_missing_image')) or raw.get('missing_media_identity'):
        reasons.append('missing_image')
    images = []
    for image in raw.get('images', []):
        try:
            file = j.safe_file(root / ('local-bank' if local else 'assets'), image['path'])
            images.append((file, image.get('alt') or '题目配图'))
        except (j.ValidationError, KeyError, TypeError):
            reasons.append('missing_image')
    subjects = raw.get('subjects', [raw.get('subject')])
    if not subjects or any(s not in j.SUBJECTS for s in subjects):
        reasons.append('invalid_subject')
    if reasons:
        return None, sorted(set(reasons)), []
    topics = list(raw.get('topics', []))
    labels = dict(topic_names) if topic_names is not None else {t['id']: t['title'] for t in j.load(root)[0]['topics']}
    for p in raw.get('provenance', []):
        original = p.get('raw', {})
        if original.get('category'):
            key = 'category-' + original['category']
            topics.append(key)
            labels[key] = CATEGORY_NAMES.get(original['category'], original['category'])
        elif original.get('chapter'):
            key = 'safe-chapter-' + str(original['chapter'])
            topics.append(key)
            labels[key] = '安全文明 · 原题库第' + str(original['chapter']) + '章'
    if not topics:
        topics = ['uncategorized']
        labels['uncategorized'] = '综合知识'
    rendered_images = [{'path': f"images/{hashlib.sha256(p.read_bytes()).hexdigest()}{p.suffix.lower()}", 'alt': alt} for p, alt in images]
    q = {k: raw[k] for k in ('id', 'stem', 'kind', 'options', 'answers', 'explanation', 'origin', 'review_status')}
    q.update(subjects=subjects, vehicles=raw.get('vehicles', []), topics=sorted(set(topics)),
             topic_labels={t: labels.get(t, t) for t in set(topics)}, images=rendered_images,
             source_label='原创法规练习' if raw['origin'] == 'original_practice' else '用户导入资料 · 2022年基准，现行答案待核验')
    q['fingerprint'] = hashlib.sha256(json.dumps(q, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
    return q, [], list(zip(images, rendered_images))


def build(source='public', root=j.ROOT):
    root = Path(root).resolve()
    output = root / 'practice-site'
    if output.exists() and not (output / '.learning-generated').is_file():
        raise j.ValidationError('practice-site 已存在且不是本工具生成目录')
    catalog, original = j.load(root)
    if source == 'local':
        questions = j.read_json(root / 'local-bank/questions.json')
    elif source == 'public':
        j.validate(catalog, original, root)
        questions = [q for q in original if j.publishable(q, catalog)]
    else:
        raise j.ValidationError('source 仅支持 public/local')
    accepted, excluded, image_copies = [], [], []
    seen = set()
    topic_names = {t['id']: t['title'] for t in catalog['topics']}
    for raw in questions:
        if raw['id'] in seen:
            raise j.ValidationError('重复题目 ID')
        seen.add(raw['id'])
        # Original images were copied into local-bank by the merge tool too.
        q, reasons, files = prepare_question(raw, root, local=source == 'local', topic_names=topic_names)
        if reasons:
            excluded.append({'id': raw['id'], 'reasons': reasons})
        else:
            accepted.append(q)
            image_copies.extend(files)
    summary = {'source': source, 'input': len(questions), 'accepted': len(accepted), 'excluded': len(excluded),
               'exclusion_reasons': dict(Counter(r for x in excluded for r in x['reasons'])),
               'vehicle_unassigned': sum(not q['vehicles'] for q in accepted),
               'complete_is_not_reviewed': True}
    with tempfile.TemporaryDirectory(prefix='.learning-stage-', dir=root) as temporary:
        stage = Path(temporary)
        shutil.copytree(root / 'web', stage, dirs_exist_ok=True)
        for (file, _alt), target in image_copies:
            destination = stage / target['path']
            destination.parent.mkdir(exist_ok=True)
            shutil.copyfile(file, destination)
        j.write_json(stage / 'data/bank.json', {'schema_version': 1, 'version': catalog['version'],
                     'summary': summary, 'vehicles': catalog['vehicles'], 'questions': accepted})
        j.write_json(stage / 'data/excluded.json', excluded)
        j.write_text(stage / '.learning-generated', 'Generated learning application')
        for name in ('LICENSE', 'LICENSE-CONTENT.md', 'NOTICE.md'):
            shutil.copyfile(root / name, stage / name)
        if output.exists():
            if output.resolve() != root / 'practice-site':
                raise j.ValidationError('输出目录越界')
            shutil.rmtree(output)
        shutil.copytree(stage, output)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=['public', 'local'], default='public')
    args = parser.parse_args()
    print(json.dumps(build(args.source), ensure_ascii=False, indent=2))
