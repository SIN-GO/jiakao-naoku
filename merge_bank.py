"""Merge a supplied ZIP as local, provenance-preserving question data.

Reads JSON and images only. SQL and bundled instructions are never executed.
Local records deliberately do not assert vehicle applicability or publishing rights.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unicodedata
from urllib.parse import unquote, urlparse
import zipfile

import jiakao as j


def norm(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value or ""))


def digest(value):
    return hashlib.sha256(value).hexdigest()


# Explicitly inspected wording pairs; never a global fuzzy substitution rule.
WORDING_PAIRS = [
    ('驾驶人发现轮胎漏气，将机动车驶离主车道时，不要采用紧急制动，以免造成翻车或后车采取制动不及时导致追尾事故。',
     '驾驶人发现轮胎漏气，将车辆驶离主车道时，不要采用紧急制动，以免造成翻车或后车采取制动不及时导致追尾事故。'),
    ('行车中遇抢救伤员的救护车从本车道逆向驶来时，要怎样做？',
     '行车中遇抢救伤员的救护车从本车道逆向驶来时，应怎样做？'),
    ('驾驶机动车遇车辆出现燃烧现象，应迅速离开车内，以免对呼吸道造成伤害或发生窒息。',
     '驾驶机动车遇车辆出现燃烧现象，应迅速离开车内，避免对呼吸道造成伤害或发生窒息。'),
]
WORDING_ALIASES = {norm(a): norm(b) for a, b in WORDING_PAIRS}


def signature(q, include_answer=True):
    # Keep signs, negation, units, numbers and images. Option reordering is safe
    # only when option texts are unique; answers are compared by text, not letters.
    options = [norm(v) for v in q['options'].values()]
    unique = len(set(options)) == len(options)
    answer = sorted(norm(q['options'][a]) for a in q['answers'])
    stem = norm(q['stem'])
    fields = [WORDING_ALIASES.get(stem, stem), q['kind'], sorted(options) if unique else options,
              sorted(i['sha256'] for i in q['images']), q.get('missing_media_identity')]
    if include_answer:
        fields.append(answer if unique else q['answers'])
    return json.dumps(fields, ensure_ascii=False, sort_keys=True)


def validate_raw(q, subject):
    if not isinstance(q, dict) or not isinstance(q.get('id'), str) or not q['id']:
        raise j.ValidationError(f'{subject}: 缺少有效 ID')
    if not isinstance(q.get('question'), str) or not q['question'].strip():
        raise j.ValidationError(f"{subject}/{q['id']}: 题干无效")
    options = q.get('options')
    if not isinstance(options, list) or not 2 <= len(options) <= 26 or not all(isinstance(v, str) and v.strip() for v in options):
        raise j.ValidationError(f"{subject}/{q['id']}: 选项无效")
    answers = q.get('answer') if isinstance(q.get('answer'), list) else [q.get('answer')]
    if (not answers or any(type(a) is not int or not 0 <= a < len(options) for a in answers)
            or len(set(answers)) != len(answers)):
        raise j.ValidationError(f"{subject}/{q['id']}: 答案下标无效")
    if q.get('type') not in {'judge', 'single', 'multiple'}:
        raise j.ValidationError('不支持的题型')
    if (q['type'] == 'multiple' and len(answers) < 2) or (q['type'] != 'multiple' and len(answers) != 1):
        raise j.ValidationError('题型与答案数量不符')
    if q['type'] == 'judge' and options != ['正确', '错误']:
        raise j.ValidationError('判断题选项错误')
    if q.get('answer_letter') != ''.join(chr(65 + a) for a in answers):
        raise j.ValidationError(f"{subject}/{q['id']}: 字母与下标答案冲突")
    return answers


def merge_records(records):
    canonical, indexed, merges = [], {}, []
    for record in records:
        key = signature(record)
        if key not in indexed:
            indexed[key] = record
            canonical.append(record)
            continue
        target = indexed[key]
        merges.append({'kept': target['id'], 'skipped': record['id'],
                       'subjects': record['subjects'], 'cross_subject': not bool(set(target['subjects']) & set(record['subjects'])),
                       'reason': 'equivalent_content' if norm(target['stem']) == norm(record['stem']) else 'inspected_wording_pair'})
        target['subjects'] = sorted(set(target['subjects'] + record['subjects']))
        for field in ('provenance', 'explanation_variants', 'law_variants'):
            for value in record[field]:
                if value not in target[field]:
                    target[field].append(value)
        if not target['explanation'] and record['explanation']:
            target['explanation'] = record['explanation']
        target['issues'] = [x for x in target['issues'] if x != 'missing_explanation' or not target['explanation']]
    return canonical, merges


def run(archive, root=j.ROOT):
    root, archive = Path(root).resolve(), Path(archive).resolve()
    output = root / 'local-bank'
    output.mkdir(exist_ok=True)
    sources, originals = j.load(root)
    records, input_stats, missing_declared = [], {}, []
    base = 'jiakao-bank/'
    archive_hash = digest(archive.read_bytes())
    with zipfile.ZipFile(archive) as z:
        if len(z.infolist()) > 30000 or sum(i.file_size for i in z.infolist()) > 1024**3:
            raise j.ValidationError('数据包超出安全读取上限')
        names = set(z.namelist())
        if len(names) != len(z.infolist()):
            raise j.ValidationError('ZIP 内存在重复文件名')
        assets_by_name = defaultdict(list)
        for name in names:
            if '/images/' in name:
                assets_by_name[PurePosixPath(name).name].append(name)
        for subject, internal in [('subject1', 'subject1'), ('subject4', 'subject3_safe')]:
            file = f'{base}{subject}/questions.json'
            rows = json.loads(z.read(file))
            if not isinstance(rows, list):
                raise j.ValidationError(f'{file}: 必须为数组')
            miss_name = f'{base}{subject}/missing_images.json'
            missing = {str(v['id']): v for v in json.loads(z.read(miss_name))} if miss_name in names else {}
            ids = set()
            input_stats[subject] = {'total': len(rows), 'types': dict(Counter(q['type'] for q in rows)),
                'missing_explanations': sum(not (q.get('explain') or '').strip() for q in rows),
                'image_references': sum(bool(q.get('image')) for q in rows),
                'declared_missing_images': len(missing)}
            for raw in rows:
                answers = validate_raw(raw, subject)
                qid = raw['id']
                if qid in ids:
                    raise j.ValidationError(f'{subject}: 重复源 ID {qid}')
                ids.add(qid)
                images, issues, absent = [], [], None
                image = raw.get('image')
                member = None
                if image:
                    path = PurePosixPath(image)
                    if path.is_absolute() or '..' in path.parts or '\\' in image:
                        raise j.ValidationError('图片路径越界')
                    member = f'{base}{subject}/{image}'
                    if member not in names:
                        absent = member
                        member = None
                if qid in missing:
                    declared = copy.deepcopy(missing[qid])
                    declared['subject'] = internal
                    absent = declared.get('image_url') or f'{subject}:{qid}'
                    # Recovery by original filename is allowed only if all candidates
                    # have identical bytes; no visually similar sign is substituted.
                    filename = PurePosixPath(unquote(urlparse(absent).path)).name
                    candidates = assets_by_name.get(filename, [])
                    if candidates and len({digest(z.read(c)) for c in candidates}) == 1:
                        member, absent = sorted(candidates)[0], None
                        declared['recovered_from'] = member
                    missing_declared.append(declared)
                if member:
                    image_bytes = z.read(member)
                    image_hash = digest(image_bytes)
                    extension = PurePosixPath(member).suffix.lower()
                    if extension not in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}:
                        raise j.ValidationError('不支持的图片类型')
                    relative = f'images/{image_hash}{extension}'
                    destination = output / relative
                    destination.parent.mkdir(exist_ok=True)
                    destination.write_bytes(image_bytes)
                    images.append({'path': relative, 'sha256': image_hash, 'source_member': member})
                if absent:
                    issues.append('missing_image')
                elif not member and re.search(r'如图|图中|动画|这种标志|这个标志|这种标线', raw['question']):
                    issues.append('possible_missing_image')
                    absent = f'unresolved:{subject}:{qid}'
                explanation = raw.get('explain') or ''
                if not explanation.strip():
                    issues.append('missing_explanation')
                provenance = {'source': f'user-zip-{subject}', 'source_id': qid, 'member': file,
                              'raw': raw}
                records.append({'id': f'bank-{subject}-{qid}', 'stem': raw['question'],
                    'kind': {'judge': 'true_false', 'single': 'single', 'multiple': 'multiple'}[raw['type']],
                    'subjects': [internal], 'vehicles': [], 'vehicle_mapping_status': 'unknown',
                    'options': {chr(65+i): text for i, text in enumerate(raw['options'])},
                    'answers': [chr(65+a) for a in answers], 'explanation': explanation,
                    'explanation_variants': [{'text': explanation, 'source_id': qid}] if explanation else [],
                    'law_variants': [{'text': raw['law'], 'source_id': qid}] if raw.get('law') else [],
                    'images': images, 'missing_media_identity': absent, 'issues': issues,
                    'review_status': 'pending', 'rights_status': 'unknown', 'origin': 'source_question',
                    'provenance': [provenance]})
    # Existing original practice remains separate from third-party source questions.
    original_records = []
    for q in originals:
        item = copy.deepcopy(q)
        item['subjects'] = [item.pop('subject')]
        item['provenance'] = [{'source': 'existing-project', 'source_id': q['id']}]
        item['explanation_variants'] = [{'text': q['explanation'], 'source_id': q['id']}]
        item['law_variants'] = []
        for img in item['images']:
            content = j.safe_file(root / 'assets', img['path']).read_bytes()
            img['sha256'] = digest(content)
            filename = f"images/{img['sha256']}{Path(img['path']).suffix}"
            (output / filename).write_bytes(content)
            img['path'] = filename
        item['missing_media_identity'], item['issues'] = None, []
        original_records.append(item)
    # Do not collapse an original exercise into an unverified external question.
    merged, duplicates = merge_records(records)
    existing_signatures = {signature(q): q['id'] for q in original_records}
    overlaps = [{'incoming': q['id'], 'existing': existing_signatures[signature(q)]}
                for q in merged if signature(q) in existing_signatures]
    overlap_ids = {q['incoming'] for q in overlaps}
    combined = original_records + [q for q in merged if q['id'] not in overlap_ids]
    stems, answer_groups = defaultdict(list), defaultdict(list)
    for q in combined:
        stems[norm(q['stem'])].append(q)
        answer_groups[signature(q, include_answer=False)].append(q)
    conflicts = [[{'id': q['id'], 'stem': q['stem'], 'answers': q['answers'], 'subjects': q['subjects']} for q in group]
                 for group in answer_groups.values() if len({signature(q) for q in group}) > 1]
    conflict_ids = {q['id'] for group in conflicts for q in group}
    for q in combined:
        if q['id'] in conflict_ids:
            q['issues'].append('answer_conflict')
            q['review_status'] = 'disputed'
    similar = []
    blocks = defaultdict(list)
    for q in combined:
        if len(norm(q['stem'])) >= 20:
            blocks[(q['kind'], norm(q['stem'])[:10], tuple(i['sha256'] for i in q['images']))].append(q)
    for block in blocks.values():
        for i, a in enumerate(block):
            for b in block[i+1:]:
                if norm(a['stem']) == norm(b['stem']):
                    continue
                ratio = SequenceMatcher(None, norm(a['stem']), norm(b['stem']), autojunk=False).ratio()
                if ratio >= 0.96:
                    similar.append({'a': a['id'], 'b': b['id'], 'similarity': round(ratio, 4), 'a_stem': a['stem'], 'b_stem': b['stem']})
    variants = [{'stem': group[0]['stem'], 'records': [{'id': q['id'], 'subjects': q['subjects'], 'answers': q['answers'],
                'images': [i['sha256'] for i in q['images']]} for q in group]}
                for group in stems.values() if len(group) > 1]
    unresolved = [{'id': q['id'], 'subjects': q['subjects'], 'stem': q['stem'], 'issues': q['issues'],
                   'missing_media_identity': q['missing_media_identity']} for q in combined if q['issues']]
    stats = {'archive': archive.name, 'archive_sha256': archive_hash, 'input': input_stats,
        'input_questions': len(records), 'existing_questions': len(originals),
        'skipped_duplicate_records': len(duplicates), 'same_subject_duplicates': sum(not x['cross_subject'] for x in duplicates),
        'inspected_wording_merges': sum(x['reason'] == 'inspected_wording_pair' for x in duplicates),
        'cross_subject_merges': sum(x['cross_subject'] for x in duplicates), 'existing_exact_overlaps': len(overlaps),
        'new_unique_questions': len(merged) - len(overlaps), 'combined_unique_questions': len(combined),
        'combined_subject_memberships': dict(Counter(s for q in combined for s in q['subjects'])),
        'same_stem_variant_groups': len(variants), 'answer_conflict_groups': len(conflicts),
        'near_duplicate_candidates': len(similar), 'issue_counts': dict(Counter(x for q in combined for x in q['issues'])),
        'images_unique_files': len({i['path'] for q in combined for i in q['images']}),
        'new_vehicle_applicability': 'unknown', 'publication': 'local_only_pending_review_and_rights'}
    j.write_json(output / 'questions.json', combined)
    for subject in j.SUBJECTS:
        j.write_json(output / f'{subject}/questions.json', [q for q in combined if subject in q['subjects']])
    for name, value in [('summary', stats), ('duplicates', duplicates), ('existing-overlaps', overlaps),
                        ('same-stem-variants', variants), ('answer-conflicts', conflicts),
                        ('near-duplicates', similar), ('unresolved', unresolved), ('missing-images', missing_declared)]:
        j.write_json(output / f'reports/{name}.json', value)
    j.write_text(output / 'README.md', f'''# 本地合并题库

从用户 ZIP 读取 JSON 和图片；没有执行 SQL、没有采用包内文档的操作指令。
原始 ZIP SHA-256：`{archive_hash}`。

输入 {len(records)} 题，现有原创 {len(originals)} 题；去重后共 {len(combined)} 道独立题目。
新增 {stats['new_unique_questions']} 题，跳过/合并 {len(duplicates)} 条重复来源记录。
科目一、科目三安全文明驾驶常识可共享题目 ID；不同科目的归属均保留。

## 使用

主数据为 questions.json，科目分片为 subject1/questions.json、subject3_safe/questions.json。
images 中为按内容哈希去重的配图，图片路径相对本目录，GIF 原样保留。
科目分片中的图片仍相对本目录，不相对分片目录。
这是本地候选数据格式，不等于已核验公开 API v1：subject 改为 subjects 数组，未确认车型为 vehicles=[]。
provenance 保留每条原始来源和原字段，explanation_variants/law_variants 保留重复来源的解析和法规差异。
答案按保留记录的选项键读取，不能将跳过记录的答案字母套在保留记录的选项上。

## 去重规则

比较 NFKC 规范化并去除空白后的题干、题型、选项文本、正确选项文本、图片内容哈希。
不忽略否定词、数字、单位或图片差异。选项顺序不同但选项文本唯一且正确答案文本一致可合并。
另核对了3组完整题干的等义改写，仅在选项、正确答案及图片一致时合并，规则以源码 WORDING_PAIRS 明列。
跨科目重复题合并存储并保留两个科目归属；同题不同答案标 disputed；相似题只列出，不自动删。
缺图题使用原图 URL 或来源 ID 隔离，防止把不同图的同题干误合并。

## 未完成内容

{json.dumps(stats['issue_counts'], ensure_ascii=False)}

没有捏造缺失图片、解析、车型或新题。所有未能补齐项列在 reports/unresolved.json。
来源包声明基于2022年题库，但没有逐题版本证据；车型适用范围、现行答案和再分发许可仍待核验。
包内“MIT可商用”的陈述仅作为附件内容，没有自动转为本项目的权利判断。
本目录及 ZIP 已加入 Git 忽略；公开 data/、generated/、dist/ 保持原有已核验样例。
''')
    report = f'''# 用户题库合并分析

## 合并结果

| 指标 | 数量 |
|---|---:|
| 科目一输入 | {input_stats['subject1']['total']} |
| 科目四输入 | {input_stats['subject4']['total']} |
| 重复或等义改写的来源记录 | {len(duplicates)} |
| 其中跨科目合并 | {stats['cross_subject_merges']} |
| 其中核对后合并的等义改写 | {stats['inspected_wording_merges']} |
| 与原项目完全重复 | {len(overlaps)} |
| 新增独立题目 | {stats['new_unique_questions']} |
| 合并后独立题目（含原4题） | {len(combined)} |
| 同题干但保留差异的组 | {len(variants)} |
| 同题同图同选项但答案冲突的组 | {len(conflicts)} |
| 待人工判定的近似题对 | {len(similar)} |

合并只针对内容完全等价记录。科目归属、来源 ID、原解析和法规文字均保留；不能把两个科目的题数相加当成去重后的独立题数。

## 缺项与覆盖

- 包内声明缺图 {len(missing_declared)} 条，能凭同名且字节一致的原图恢复 {sum('recovered_from' in m for m in missing_declared)} 条。
- 实际科目四图片引用 {input_stats['subject4']['image_references']} 次；说明文字的639是图片文件数，不能代替引用题数。
- 原始空解析共 {sum(x['missing_explanations'] for x in input_stats.values())} 条；去重与复用已有解析后的待处理项：`{json.dumps(stats['issue_counts'], ensure_ascii=False)}`。
- 未提供题目适用车型字段，新增题目不分配到A/B/C/D等车型，不宣称全车型补齐。
- 未确认所有原始答案的时效性；空解析和缺图没有用推测内容填充。

## 本地产物

完整合并库：`local-bank/questions.json`；分科目 JSON、离线图片和逐题报告在同目录。
详细报告包含 duplicates、same-stem-variants、answer-conflicts、near-duplicates、unresolved、missing-images。
执行 `python merge_bank.py "驾考题库数据包(2).zip"` 可重新生成。原始 ZIP 不修改，现有公开题库不覆盖。
第三方内容暂仅本地保存，待逐题复核、车型映射及权利核查后再进入公开发布流程。
'''
    j.write_text(root / 'docs/IMPORT-REPORT.md', report)
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.archive), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        parser.exit(1, f'导入失败: {exc}\n')


if __name__ == '__main__':
    main()
