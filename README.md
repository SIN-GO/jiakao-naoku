# 驾考脑库 · Jiakao Study Bank

[English guide](README.en.md) · [使用说明](docs/LEARNING.md) · [数据来源与权威性](docs/DATA-PROVENANCE.md) · [局限性与免责声明](docs/DISCLAIMER.md)

把驾考知识按考点组织起来：离线笔记、可调用 JSON、知识卡、练习、错题解析和间隔复习。

**当前公开版本：0.1.0，4 道原创法规练习，非官方真题、非完整题库。**
17 种准驾车型分类已建立；不代表已收齐各车型内容。网页源码保留，仅用于本地运行，**不部署、不启用 GitHub Pages**。

## 你能得到什么

- **离线知识库**：每题一篇 Markdown，试题与考点双向链接，图片随包提供，可用 Obsidian 或 GitHub 阅读。
- **静态数据接口**：按车型和科目导出 UTF-8 JSON，适合其他学习工具读取。
- **学习与练习**：知识卡先理解，再隐藏答案作答；提交后查看原解析。
- **完整题过滤**：缺题干、选项、有效答案、解析或必要图片的题，不进入学习和练习池；争议题排除。
- **错题复习**：答错或不确定自动排队；到期答对推进间隔，再次答错重新开始。
- **个性化任务**：设置目标日期与每日时间，结合已练进度和到期错题生成任务，并记录实操阶段目标。

## 快速开始

### 离线笔记与数据

下载仓库 ZIP 或克隆项目，用 Obsidian 打开 `generated/vault`。

- [使用说明](generated/vault/00-使用说明.md) · [考点入口](generated/vault/20-考点/00-总览.md)
- [覆盖统计](generated/vault/覆盖统计.md) · [JSON 清单](generated/api/v1/manifest.json) · [字段与读取示例](docs/API.md)

### 本地学习应用

需要 **Python 3.11+**；本地预览和 JavaScript 测试需要 **Node.js 20+**。
Python 工具无第三方运行依赖；网页无 npm 安装步骤。

```sh
python jiakao.py validate
python build_learning.py --source public
node serve.mjs
```

打开终端显示的本机地址，默认 `http://127.0.0.1:8765`。终端保持运行，结束时按 Ctrl+C。
Windows 也可运行 `.\start-learning.ps1 -Source public`。
公开仓库默认仅含4道样例；它不会自动下载商业题库或用户本地资料。

如果你自己持有兼容且有权使用的数据包，可在本地执行：

```sh
python merge_bank.py "你的题库.zip"
python build_learning.py --source local
node serve.mjs
```

导入格式见 [本地合并说明](docs/IMPORT-REPORT.md)。转换器当前读取 `jiakao-bank/subject1/questions.json`、
`jiakao-bank/subject4/questions.json` 及各科图片；不会执行附件中的 SQL 或操作指令。
本地题库、网页构建产物和个人进度不纳入公开包。[完整学习使用说明](docs/LEARNING.md)

## 艾宾浩斯遗忘规律启发的学习法

不是一次把同一道题刷很多遍，而是在间隔一段时间后主动回想，再核对答案：

1. **围绕薄弱点分配时间**：答错或不确定的题自动进入复习，减少遗漏。
2. **理解后再提取**：先学解析，练习时隐藏答案，避免把“看着熟悉”当作已经记住。
3. **形成持续复习节奏**：到期队列帮助把复习分散到多天，降低临考前积压。
4. **根据表现调整**：到期答对逐步延长间隔，再答错重新安排；提前重练不跳级。

默认间隔为 **10分钟 → 1天 → 3天 → 7天 → 14天 → 30天**，从每次到期作答时间计算下一次。
这组数字是产品默认值，不是对艾宾浩斯实验的精确复刻，也不是已经拟合的个人遗忘曲线。
不能保证优于所有其他安排或保证考试通过。
间隔提取对记忆的支持及其边界见 [Karpicke & Bauernschmidt（2011）](https://pubmed.ncbi.nlm.nih.gov/21574747/)。

## 数据来源、权威性与时效性

| 内容 | 当前状态 |
|---|---|
| 官方法规参考 | 公开样例列明政府网站法规链接及条号；法规权威性不等于本项目获得官方背书 |
| 公开题目 | 4道独立创作的法规练习，经AI辅助资料对照，未经独立人工审校 |
| 用户本地资料 | 原3948条，合并后3765道独立题；排除192道不完整题，可练3573道；**不随公开仓库或发布包分发** |
| 社区题库版本 | 附件及上游声明以2022-07-17快照为基准，部分更新声明尚未逐题核实 |
| 车型与地区 | 新增导入资料无明确车型字段；不自动分配，不承诺地方题、所有车型或所有申领情形覆盖 |

[来源与权威性明细](docs/DATA-PROVENANCE.md) · [候选题源调查](docs/SOURCES.md) · [本地合并报告](docs/IMPORT-REPORT.md)

核查记录截至 **2026-11-13**。核查日期不代表持续更新；尚未确认所有后续法规修订。
公开练习不是最新官方考试题库；正式备考请核对最新官方规定与当地考试要求。
附件声称的“MIT/可商用”不作为第三方题干、解析、图片的完整授权证明。

## 局限性、隐私与免责声明

内容可能错误或过期，完整性过滤不保证答案正确；题库、分类和车型范围并不完整。
不代表公安部、车管所、驾校或任何商业平台，不承诺押题、通过率或取得驾驶资格。
实操里程碑不替代教练培训。不得用于考试作弊或违规驾驶。
学习记录保存在当前浏览器，可导出备份；无云同步，网页关闭后不推送提醒。
[完整中英文免责声明](docs/DISCLAIMER.md) · [隐私、安全与权利报告](SECURITY.md)

## 开发、验证与发布

```sh
python -m unittest discover -s tests -v
node --test tests/learning.test.mjs
node --check web/app.mjs
python jiakao.py build
python jiakao.py package
python prepare_publication.py
```

只修改 `data/`、`assets/` 与源码，再生成 `generated/`。
发布工具按白名单生成独立目录、源码 ZIP、离线笔记 ZIP、API ZIP、文件清单及 SHA-256 校验。
`release-bundles/` 和 `publish-ready/` 仅为本地发布准备目录，不递归打入包中。
[GitHub 规则落实](docs/GITHUB-PUBLISHING.md) · [发布流程](docs/RELEASING.md) · [贡献方式](CONTRIBUTING.md)

## 许可与致谢

工具代码采用 [MIT](LICENSE)；本项目原创内容采用 [CC BY 4.0](LICENSE-CONTENT.md)。
第三方内容不由这两份许可重新授权，见 [NOTICE](NOTICE.md)。
参考 [ERRRC/kaogongzhentizhengliu](https://github.com/ERRRC/kaogongzhentizhengliu) 的知识网络使用思路，未复制其题库或解析。
