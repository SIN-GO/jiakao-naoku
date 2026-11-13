"""Dependency-free data validation, import, vault export and release packaging."""
from __future__ import annotations

import argparse
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import quote, unquote, urlparse
import zipfile

ROOT = Path(__file__).resolve().parent
SUBJECTS = {"subject1": "科目一", "subject3_safe": "科目三安全文明驾驶常识"}
VEHICLES = dict(zip(
    "A1 A2 A3 B1 B2 C1 C2 C3 C4 C5 C6 D E F M N P".split(),
    ["大型客车", "重型牵引挂车", "城市公交车", "中型客车", "大型货车", "小型汽车",
     "小型自动挡汽车", "低速载货汽车", "三轮汽车", "残疾人专用小型自动挡载客汽车",
     "轻型牵引挂车", "普通三轮摩托车", "普通二轮摩托车", "轻便摩托车",
     "轮式专用机械车", "无轨电车", "有轨电车"]))
ID = re.compile(r"[a-z][a-z0-9-]{1,79}\Z")


class ValidationError(ValueError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def iso_date(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def safe_file(root, relative):
    if not nonempty(relative) or "\\" in relative or Path(relative).is_absolute():
        raise ValidationError(f"非法相对路径: {relative}")
    root = Path(root).resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValidationError(f"文件不存在或越界: {relative}")
    return target


def load(root=ROOT):
    root = Path(root)
    return read_json(root / "data/catalog.json"), read_json(root / "data/questions.json")


def validate(catalog, questions, root=ROOT):
    """All drafts must be structurally valid; only reviewed/cleared records export."""
    errors = []
    def check(ok, message):
        if not ok:
            errors.append(message)
    if not isinstance(catalog, dict) or not isinstance(questions, list):
        raise ValidationError("catalog 必须为对象，questions 必须为数组")
    check(catalog.get("schema_version") == "1.0", "不支持的 schema_version")
    check(bool(re.fullmatch(r"\d+\.\d+\.\d+", str(catalog.get("version", "")))), "无效版本")
    check(iso_date(catalog.get("as_of")), "缺少有效 as_of")
    vehicle_rows = catalog.get("vehicles", [])
    check(isinstance(vehicle_rows, list) and all(isinstance(v, dict) for v in vehicle_rows), "vehicles 格式错误")
    if errors:
        raise ValidationError("\n".join(errors))
    check({v.get("code") for v in vehicle_rows} == set(VEHICLES) and len(vehicle_rows) == len(VEHICLES), "车型必须完整且无重复")
    for v in vehicle_rows:
        check(v.get("name") == VEHICLES.get(v.get("code")), "车型名称错误")
        check(v.get("exam_mapping_status") in {"pending", "reviewed"}, "考试映射状态无效")
        check(nonempty(v.get("exam_note")), "缺少考试适用说明")
    maps = {}
    for kind in ("sources", "topics"):
        rows = catalog.get(kind, [])
        check(isinstance(rows, list) and all(isinstance(r, dict) for r in rows), f"{kind} 格式错误")
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            continue
        maps[kind] = {r.get("id"): r for r in rows if isinstance(r.get("id"), str)}
        check(len(maps[kind]) == len(rows), f"{kind} ID 重复或缺失")
        for row in rows:
            check(isinstance(row.get("id"), str) and bool(ID.fullmatch(row["id"])), f"{kind} ID 非法")
            check(nonempty(row.get("title")), f"{kind} 缺少标题")
    if errors:
        raise ValidationError("\n".join(errors))
    for source in maps["sources"].values():
        check(urlparse(source.get("url", "")).scheme in {"https", "http"}, "来源 URL 无效")
        check(iso_date(source.get("checked_at")), "来源缺少核查日期")
        check(nonempty(source.get("version")), "来源缺少版本")
        check(source.get("redistribution") in {"cleared", "unknown", "restricted", "reference_only"}, "来源许可状态无效")
        for part in ("stem_terms", "explanation_terms", "image_terms"):
            check(nonempty(source.get(part)), f"来源缺少 {part}")
    for topic in maps["topics"].values():
        check(nonempty(topic.get("summary")), "考点缺少 summary")
    seen = set()
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            errors.append(f"第 {i} 条题目不是对象")
            continue
        qid = q.get("id")
        prefix = str(qid or i)
        valid_id = isinstance(qid, str) and bool(ID.fullmatch(qid))
        check(valid_id, f"{prefix}: 非法 ID")
        if valid_id:
            check(qid not in seen, f"{prefix}: 重复 ID")
            seen.add(qid)
        for field in ("stem", "explanation", "reasoning", "pitfall", "version", "license"):
            check(nonempty(q.get(field)), f"{prefix}: 缺少 {field}")
        check(q.get("subject") in SUBJECTS, f"{prefix}: 科目无效")
        vehicles = q.get("vehicles")
        check(isinstance(vehicles, list) and bool(vehicles) and all(isinstance(v, str) and v in VEHICLES for v in vehicles) and len(vehicles) == len(set(v for v in vehicles if isinstance(v, str))), f"{prefix}: 车型无效")
        check(q.get("kind") in {"true_false", "single", "multiple"}, f"{prefix}: 题型无效")
        options, answers = q.get("options"), q.get("answers")
        check(isinstance(options, dict) and len(options) >= 2 and all(re.fullmatch("[A-Z]", k) and nonempty(v) for k, v in options.items()), f"{prefix}: 选项无效")
        valid_answers = isinstance(answers, list) and bool(answers) and all(isinstance(a, str) for a in answers)
        check(valid_answers and isinstance(options, dict) and len(answers) == len(set(answers)) and all(a in options for a in answers), f"{prefix}: 答案无效")
        if valid_answers:
            check(len(answers) >= 2 if q.get("kind") == "multiple" else len(answers) == 1, f"{prefix}: 答案数量错误")
        if q.get("kind") == "true_false":
            check(options == {"A": "正确", "B": "错误"}, f"{prefix}: 判断题须使用 A正确/B错误")
        for field, mapping in (("topics", maps["topics"]), ("sources", maps["sources"])):
            values = q.get(field)
            check(isinstance(values, list) and bool(values) and all(isinstance(v, str) and v in mapping for v in values), f"{prefix}: {field} 引用无效")
        check(q.get("origin") in {"original_practice", "source_question"}, f"{prefix}: origin 无效")
        check(q.get("rights_status") in {"cleared", "unknown", "restricted"}, f"{prefix}: 权限状态无效")
        check(q.get("review_status") in {"reviewed", "pending", "disputed"}, f"{prefix}: 复核状态无效")
        check(nonempty(q.get("review_note")), f"{prefix}: 缺少复核说明")
        check(isinstance(q.get("images"), list), f"{prefix}: images 须为数组")
        check(isinstance(q.get("evidence"), list), f"{prefix}: evidence 须为数组")
        if q.get("review_status") == "reviewed":
            check(iso_date(q.get("reviewed_at")) and nonempty(q.get("reviewer")), f"{prefix}: 缺少复核日期或人员")
            check(isinstance(q.get("evidence"), list) and bool(q["evidence"]), f"{prefix}: 缺少答案依据")
        for evidence in q.get("evidence", []) if isinstance(q.get("evidence"), list) else []:
            check(isinstance(evidence, dict) and evidence.get("source_id") in maps["sources"] and nonempty(evidence.get("locator")), f"{prefix}: 答案依据无效")
        for img in q.get("images", []) if isinstance(q.get("images"), list) else []:
            if not isinstance(img, dict):
                errors.append(f"{prefix}: 图片格式错误")
                continue
            check(nonempty(img.get("alt")) and nonempty(img.get("license")), f"{prefix}: 缺少图片说明或许可")
            check(img.get("source_id") in maps["sources"], f"{prefix}: 图片来源无效")
            try:
                safe_file(Path(root) / "assets", img.get("path"))
            except ValidationError as exc:
                errors.append(f"{prefix}: {exc}")
    if errors:
        raise ValidationError("\n".join(errors))


def publishable(q, catalog):
    sources = {s["id"]: s for s in catalog["sources"]}
    content_sources = q["sources"] + [i["source_id"] for i in q["images"]]
    return (q["review_status"] == "reviewed" and q["rights_status"] == "cleared"
            and all(sources[s]["redistribution"] == "cleared" for s in content_sources)
            and all(sources[e["source_id"]]["redistribution"] in {"cleared", "reference_only"}
                    for e in q["evidence"]))


def md_link(label, path):
    return f"[{label}]({quote(str(path).replace(chr(92), '/'), safe='/.-')})"


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def coverage(catalog, questions):
    rows = []
    for v in catalog["vehicles"]:
        for subject in SUBJECTS:
            qs = [q for q in questions if v["code"] in q["vehicles"] and q["subject"] == subject]
            exported = [q for q in qs if publishable(q, catalog)]
            rows.append({"vehicle": v["code"], "subject": subject, "collected": len(qs),
                         "reviewed": sum(q["review_status"] == "reviewed" for q in qs), "published": len(exported),
                         "last_reviewed_at": max((q["reviewed_at"] for q in qs if q["review_status"] == "reviewed"), default=None),
                         "status": "partial" if exported else "pending", "gap": "非完整题库；专属题及最新变化待补充",
                         "exam_mapping_status": v["exam_mapping_status"], "exam_note": v["exam_note"]})
    return rows


def build(root=ROOT, output=None):
    root = Path(root).resolve()
    output = Path(output or root / "generated").resolve()
    # Prevent replacing user/source directories, even when a caller supplies --output.
    if output.exists() and not (output / ".jiakao-generated").is_file():
        raise ValidationError("输出目录已存在且不是本工具生成目录，请指定空的新目录")
    if output == root or output in root.parents or any(output == root / d for d in ("data", "assets", "docs", "tests")):
        raise ValidationError("输出目录不能覆盖源文件")
    catalog, questions = load(root)
    validate(catalog, questions, root)
    published = sorted((q for q in questions if publishable(q, catalog)), key=lambda q: q["id"])
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="jiakao-", dir=output.parent) as tmp:
        stage = Path(tmp)
        api, vault = stage / "api/v1", stage / "vault"
        write_json(api / "questions.json", published)
        public_catalog = copy.deepcopy(catalog)
        # Candidate investigations remain in docs, not in the released catalog.
        public_catalog["sources"] = [s for s in catalog["sources"] if s["redistribution"] in {"cleared", "reference_only"}]
        write_json(api / "catalog.json", public_catalog)
        rows = coverage(catalog, questions)
        write_json(api / "coverage.json", rows)
        partitions = []
        for v in VEHICLES:
            for subject in SUBJECTS:
                selected = [q for q in published if v in q["vehicles"] and q["subject"] == subject]
                rel = f"vehicles/{v}/{subject}.json"
                write_json(api / rel, selected)
                partitions.append({"vehicle": v, "subject": subject, "path": rel, "count": len(selected)})
        write_json(api / "manifest.json", {"schema_version": "1.0", "version": catalog["version"], "as_of": catalog["as_of"],
                    "unique_questions": len(published), "complete": False, "catalog": "catalog.json", "coverage": "coverage.json",
                    "questions": "questions.json", "partitions": partitions})
        topic_links = []
        for topic in catalog["topics"]:
            qs = [q for q in published if topic["id"] in q["topics"]]
            topic_links.append(md_link(topic["title"], f"{topic['id']}.md"))
            body = f"# {topic['title']}\n\n{topic['summary']}\n\n## 关联练习\n\n"
            body += "\n".join("- " + md_link(q["stem"], f"../10-试题/{q['id']}.md") for q in qs) or "待补充。"
            write_text(vault / f"20-考点/{topic['id']}.md", body)
        write_text(vault / "20-考点/00-总览.md", "# 考点导航\n\n" + "\n".join("- " + x for x in topic_links))
        for s in public_catalog["sources"]:
            write_text(vault / f"15-法规与标志/{s['id']}.md", f"# {s['title']}\n\n来源：[{s['title']}]({s['url']})\n\n版本：{s['version']}；核查日期：{s['checked_at']}。\n\n题干：{s['stem_terms']}\n\n解析：{s['explanation_terms']}\n\n图片：{s['image_terms']}\n\n正文未随库复制。")
        for q in published:
            front = {"id": q["id"], "subject": q["subject"], "vehicles": q["vehicles"], "origin": q["origin"],
                     "tags": [f"驾考/{q['subject']}"] + [f"车型/{v}" for v in q["vehicles"]]}
            text = "---\n" + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in front.items()) + "\n---\n"
            text += f"# {q['stem']}\n\n{'原创法规练习，非官方真题。' if q['origin'] == 'original_practice' else '来源题，非官方背书。'}\n\n"
            text += f"科目：{SUBJECTS[q['subject']]}；适用车型：{', '.join(q['vehicles'])}\n\n"
            for img in q["images"]:
                target = safe_file(root / "assets", img["path"])
                destination = vault / "90-图片" / img["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(target, destination)
                text += "!" + md_link(img["alt"], "../90-图片/" + img["path"]) + "\n\n"
            text += "\n".join(f"- {k}. {v}" for k, v in q["options"].items())
            text += f"\n\n## 答案\n\n{', '.join(q['answers'])}\n\n## 解析\n\n{q['explanation']}\n\n## 解题思路\n\n{q['reasoning']}\n\n## 易错点\n\n{q['pitfall']}\n\n## 相关考点\n\n"
            text += "\n".join("- " + md_link(t, f"../20-考点/{t}.md") for t in q["topics"])
            text += "\n\n## 答案依据\n\n" + "\n".join("- " + md_link(e["locator"], f"../15-法规与标志/{e['source_id']}.md") for e in q["evidence"])
            text += "\n\n## 内容来源与许可\n\n" + "\n".join("- " + md_link(s, f"../15-法规与标志/{s}.md") for s in q["sources"])
            text += f"\n\n许可：{q['license']}；版本：{q['version']}。\n\n复核：{q['reviewed_at']} / {q['reviewer']}；{q['review_note']}"
            write_text(vault / f"10-试题/{q['id']}.md", text)
        # Do not ship unreviewed/restricted question text, images or answer guesses.
        withheld = [{"id": q["id"], "review_status": q["review_status"], "rights_status": q["rights_status"]} for q in questions if not publishable(q, catalog)]
        write_text(vault / "30-疑点复核/疑点清单.md", "# 疑点与暂缓发布\n\n仅公开状态，不发布待核实题目内容。\n\n" + ("\n".join(f"- {q['id']}：{q['review_status']} / {q['rights_status']}" for q in withheld) or "暂无。"))
        table = "| 车型 | 科目 | 收录 | 已核验 | 已发布 | 最近核验 | 缺口 |\n|---|---|---:|---:|---:|---|---|\n"
        table += "\n".join(f"| {r['vehicle']} | {SUBJECTS[r['subject']]} | {r['collected']} | {r['reviewed']} | {r['published']} | {r['last_reviewed_at'] or '—'} | {r['gap']} |" for r in rows)
        write_text(vault / "覆盖统计.md", "# 覆盖统计\n\n收录和已核验可包含尚未获再分发许可的记录；已发布才是可调用数量。两行不代表该车型必须分别参加两场考试。\n\n" + table)
        write_text(vault / "00-使用说明.md", "# 驾考脑库\n\n原创法规练习样例，非完整题库、非官方真题；不代表官方考试覆盖范围。\n\n" + md_link("从考点开始", "20-考点/00-总览.md") + " · " + md_link("覆盖统计", "覆盖统计.md") + " · " + md_link("疑点复核", "30-疑点复核/疑点清单.md") + "\n\n用 Obsidian 打开本文件所在文件夹；局部关系图可查看相邻考点。生成文件请勿直接编辑，修正源数据后重新构建。")
        write_json(vault / ".obsidian/graph.json", {"search": "path:20-考点", "showAttachments": False})
        for name in ("LICENSE", "LICENSE-CONTENT.md", "NOTICE.md"):
            shutil.copyfile(root / name, vault / name)
            shutil.copyfile(root / name, stage / "api" / name)
        shutil.copyfile(root / "docs/API.md", stage / "api/README.md")
        check_links(vault)
        write_text(stage / ".jiakao-generated", "Generated by jiakao; do not edit.")
        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(stage, output)
    return {"published": len(published), "withheld": len(questions) - len(published), "output": str(output)}


def check_links(folder):
    folder = Path(folder).resolve()
    for path in folder.rglob("*.md"):
        for url in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if urlparse(url).scheme or url.startswith("#"):
                continue
            target = (path.parent / unquote(url.split("#")[0])).resolve()
            if not target.is_relative_to(folder) or not target.is_file():
                raise ValidationError(f"断链: {path.name} -> {url}")


def import_questions(path, root=ROOT):
    root = Path(root)
    catalog, existing = load(root)
    incoming = read_json(path)
    if not isinstance(incoming, list):
        raise ValidationError("导入文件必须为题目数组")
    combined = existing + incoming  # Duplicate IDs fail instead of silently overwriting.
    validate(catalog, combined, root)
    destination = root / "data/questions.json"
    temporary = destination.with_suffix(".json.tmp")
    write_json(temporary, combined)
    temporary.replace(destination)
    return {"imported": len(incoming), "total": len(combined)}


def package(root=ROOT, output=None):
    root = Path(root)
    result = build(root, output)
    generated = Path(result["output"])
    version = load(root)[0]["version"]
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    paths = []
    for kind in ("vault", "api"):
        archive = dist / f"jiakao-{kind}-{version}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted((generated / kind).rglob("*")):
                if p.is_file():
                    info = zipfile.ZipInfo(p.relative_to(generated).as_posix(), (2026, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    z.writestr(info, p.read_bytes())
        paths.append(archive)
    write_text(dist / "SHA256SUMS", "\n".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in paths))
    return {**result, "archives": [str(p) for p in paths]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("validate")
    for name in ("build", "package"):
        subs.add_parser(name).add_argument("--output", type=Path)
    subs.add_parser("import").add_argument("file", type=Path)
    subs.add_parser("check-links").add_argument("folder", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            validate(*load(args.root), args.root)
            result = {"valid": True}
        elif args.command == "build":
            result = build(args.root, args.output)
        elif args.command == "package":
            result = package(args.root, args.output)
        elif args.command == "import":
            result = import_questions(args.file, args.root)
        else:
            check_links(args.folder)
            result = {"links_valid": True}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValidationError, OSError, ValueError, TypeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
