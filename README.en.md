# Jiakao Study Bank · 驾考脑库

[中文说明](README.md) · [Provenance and authority](docs/DATA-PROVENANCE.md) · [Limitations and disclaimer](docs/DISCLAIMER.md)

A study toolkit for mainland China's driving-license theory knowledge: linked offline notes,
static JSON, knowledge cards, practice, explanations and spaced review.

**Public version 0.1.0 contains four original regulatory exercises, not official exam questions or a complete question bank.**
The catalog covers 17 vehicle codes, which does not imply complete vehicle-specific content.
Web application source is retained for local use; **no website is deployed and GitHub Pages remains disabled**.

## Features

- One Markdown note per question, backlinks to topics, and bundled offline images.
- UTF-8 JSON exports partitioned by vehicle and subject for other learning tools.
- Knowledge cards followed by practice with answers hidden until submission.
- Structural completeness filtering: missing stems, options, answers, explanations or required images are excluded, as are disputed answers.
- Wrong or uncertain answers enter a review queue; successful due reviews advance the interval, while errors restart it.
- Plans based on a target date, daily time, coverage and due reviews, plus user-managed driving-training milestones.

## Quick start

Download or clone the repository. Open `generated/vault` as an Obsidian vault, or browse the notes on GitHub.

- [Note guide](generated/vault/00-使用说明.md) · [Topics](generated/vault/20-考点/00-总览.md)
- [Coverage](generated/vault/覆盖统计.md) · [JSON manifest](generated/api/v1/manifest.json) · [API fields and examples](docs/API.md)

Python tooling requires **Python 3.11+**, with no third-party runtime dependencies.
Local preview and JavaScript tests require **Node.js 20+**; no npm install is needed.

```sh
python jiakao.py validate
python build_learning.py --source public
node serve.mjs
```

Open the printed local address, normally `http://127.0.0.1:8765`. Keep the terminal running; stop with Ctrl+C.
Windows users may run `.\start-learning.ps1 -Source public`.
The public checkout contains only the four original examples and never automatically downloads a third-party bank.

If you possess a compatible archive that you are entitled to use, import it locally:

```sh
python merge_bank.py "your-bank.zip"
python build_learning.py --source local
node serve.mjs
```

The importer expects `jiakao-bank/subject1/questions.json`, `jiakao-bank/subject4/questions.json`
and their images. It does not execute attached SQL or document instructions.
Local data, rendered app output and personal progress are excluded from the public package.
[Import results](docs/IMPORT-REPORT.md) · [Detailed learning guide (Chinese)](docs/LEARNING.md)

## Why use an Ebbinghaus-inspired study workflow?

Instead of repeatedly viewing the same answer in one sitting, attempt to retrieve it after a delay:

1. **Focus effort on weak items:** wrong or uncertain answers are automatically scheduled.
2. **Separate recognition from recall:** learn the explanation, then answer without seeing it.
3. **Build a sustainable routine:** a due queue distributes review across days and exposes unfinished work.
4. **Adapt to performance:** successful due reviews lengthen the interval; errors restart the cycle.

Default intervals are **10 minutes → 1 day → 3 days → 7 days → 14 days → 30 days**,
measured from each due review. Early practice does not advance the schedule.
These are product defaults, not an exact reconstruction of Ebbinghaus's experiments or a fitted personal forgetting curve.
They are not claimed to outperform every alternative schedule or guarantee exam success.
For evidence and limits of spaced retrieval, see [Karpicke & Bauernschmidt (2011)](https://pubmed.ncbi.nlm.nih.gov/21574747/).

## Learning, review and planning

Select a subject and vehicle scope, read knowledge cards, then practice in rounds of up to 20 items.
Wrong/uncertain answers show their source explanation and enter review. Only due reviews advance the cycle.
Defaults are a 30-day target and 30 minutes/day; dates and daily time are editable.
Plans prioritize due work, estimate new-item capacity and flag insufficient time without marking overdue work complete.
Registration, theory, practical training, safety knowledge and licensing milestones have editable target dates.
They do not replace qualified instruction or determine legal eligibility, required hours or booking rules.

Progress is stored in the current browser, with JSON export/restore. There is no automatic cloud sync
or notification while the page is closed. Back up before clearing storage, changing origins or switching devices.

## Sources, authority and freshness

| Material | Status |
|---|---|
| Regulatory references | Government-hosted provisions cited per exercise; this does not make the project officially endorsed |
| Public questions | Four independently written exercises with AI-assisted reference checks, without independent human review |
| User-supplied local archive | 3,948 input records; 3,765 unique questions including four originals; 192 incomplete items excluded, leaving 3,573 for local practice; **not distributed publicly** |
| Community data vintage | Attachment/upstream claims point to a 2022-07-17 snapshot; later-update claims are not verified per record |
| Vehicle/region scope | Imported records have no verified vehicle mapping; local/regional and all application scenarios are not established |

Review records are dated **2026-11-13**. A check date is not continuous monitoring or proof that no later rules exist.
Consult current official regulations and local requirements before an exam or driving.
An attachment's MIT/commercial-use claim is not treated as proof of every third-party text/image right.
[Provenance details](docs/DATA-PROVENANCE.md) · [Source investigation](docs/SOURCES.md)

## Limitations, licensing and reports

Answers may be incorrect or outdated; filtering completeness does not establish correctness.
The bank and vehicle mappings are incomplete. No official affiliation, prediction, pass rate or driving eligibility is promised.
Do not use the project for cheating or unlawful driving. [Full bilingual disclaimer](docs/DISCLAIMER.md)

Code: [MIT](LICENSE). Original content: [CC BY 4.0](LICENSE-CONTENT.md).
Third-party materials are not relicensed by these notices. [NOTICE](NOTICE.md) · [Security/privacy/rights reports](SECURITY.md)
The knowledge-network approach was inspired by [ERRRC/kaogongzhentizhengliu](https://github.com/ERRRC/kaogongzhentizhengliu);
its question content and explanations were not copied.

## Development and release preparation

```sh
python -m unittest discover -s tests -v
node --test tests/learning.test.mjs
node --check web/app.mjs
python jiakao.py build
python jiakao.py package
python prepare_publication.py
```

Edit source data/code, then regenerate `generated/`. Publication uses an allowlist to create a separate source directory,
source/vault/API ZIPs, a per-file manifest and SHA-256 checksums. No recursive workspace upload is required.
The local `publish-ready/` and `release-bundles/` directories are excluded from their own archives.
[GitHub publishing rules](docs/GITHUB-PUBLISHING.md) · [Release procedure](docs/RELEASING.md) · [Contributing](CONTRIBUTING.md)
