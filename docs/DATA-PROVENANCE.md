# 数据来源、权威性、时效性 / Data provenance, authority and freshness

记录日期 / Recorded: **2026-11-13**。

| 层级 / Layer | 来源 / Source | 能证明什么 / What it supports | 不能证明什么 / What it does not establish |
|---|---|---|---|
| 法规参考 / Regulatory reference | [公安部令第172号修订的规定，政府网站文本](https://www.beijing.gov.cn/zhengce/zhengcefagui/qtwj/202412/t20241231_3978134.html)；2024-12-21公布、2025-01-01施行 | 样例所列条号的核验依据 / Reference for cited provisions | 本项目获得官方认可、题库完整、覆盖全部后续修订 / Official endorsement, full bank coverage, or every later amendment |
| 本项目公开样例 / Public samples | data/questions.json，4道独立编写的法规练习 | 逐题出处、核验日期、AI辅助核查身份和许可 / Per-record references, review date/type and original-content license | 官方真题或独立人工复核 / Official exam questions or independent human review |
| 用户提供资料 / Supplied material | 本地ZIP，SHA-256见local-bank报告；原始3948条 | 本地合并过程可追溯 / Traceable local import | 该ZIP中的许可、更新、车型声明已经获证实 / Verified licensing, currency or vehicle applicability |
| 科目一社区来源 / Community Subject 1 source | 附件声称来自[AgentMystia/driving-test-subject1](https://github.com/AgentMystia/driving-test-subject1) | 上游README写明原数据来自banban驾道、2022-07-17快照，并列出局限 / Upstream identifies banban and a 2022 snapshot with limitations | 代码MIT能够授权所有题干、解析与图片 / A code license granting every dataset/image right |
| 科目四社区来源 / Community safety-knowledge source | 附件声称来自[benchjx/DriverEasy](https://github.com/benchjx/DriverEasy) | 候选来源链接 / Candidate provenance link | 已逐题匹配到该仓库某个提交，或已确认全部素材授权 / Commit-level verification or full rights clearance |
| 更上游 / Earlier upstream | [doupoa/DrivingTestSubjectOne](https://github.com/doupoa/DrivingTestSubjectOne) | README标明banban驾道及2022-07-17日期 / Declared source and snapshot date | 官方公开题库或2026最新完整数据 / Official bank or a complete current bank |

本地合并后有3765道独立题（含原4道样例），其中192道不完整被排除，剩余3573道。
公开数据包仍为4道原创练习。两种统计不能混用。
The local merged collection contains 3,765 unique questions including four originals; 192 incomplete records are excluded from local practice, leaving 3,573. Public data contains only four original exercises.

## 时效性 / Freshness

- 2022年基准及2025年修订等说明来自附件或上游声明；没有逐题证明已更新到当前考试。
  Snapshot/update statements are source claims, not record-by-record verification of the current exam.
- `checked_at`/`reviewed_at`表示一次核查日期，不是自动更新承诺，也不能证明此后法规未变。
  A review date records a check, not continuous monitoring or absence of later changes.
- 未独立核验新能源、地方补充题、所有准驾车型专属题、所有初领/增驾/恢复资格情形。
  New-energy, regional, vehicle-specific and application-scenario coverage is not established.
- 正式备考应核对最新官方规定和当地考试要求；有争议的答案先撤出公开练习，再核验。
  Consult current official rules and local exam requirements; withdraw disputed answers pending review.

## 第三方授权边界 / Third-party rights

附件中“MIT、可商用”等句子属于待核查的来源声明。没有把它当作本项目重新授权第三方题库的依据。
Claims such as “MIT/commercial use allowed” in the attachment are unverified source statements, not authority for this project to relicense third-party material.
获得授权后还需保留原许可证、署名、版本和权利人要求，再进入公开数据源；不以免责声明替代授权。
Future imports require evidence of rights, original notices, attribution and version provenance; disclaimers are not permission.
