# GitHub 发布准备 / GitHub publication readiness

核查日期 / Checked: **2026-11-13**。以下为对官方文档的项目级落实，不是 GitHub 审核通过证明或法律意见。

| 官方依据 / Official reference | 项目落实 / Implementation |
|---|---|
| [Acceptable Use Policies](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies) | 尊重知识产权、隐私和真实性；不把社区题库标成官方授权题库。Respect IP, privacy and authenticity; no claim of official endorsement. |
| [Adding files](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository) | 浏览器每文件25 MiB、每批100文件；发布清单检查大小并可分批上传。Browser uploads: 25 MiB/file and 100 files/batch; verify manifest and batch as needed. |
| [Large files](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) | 常规Git阻止超过100 MiB的文件；不将原始ZIP、运行缓存或完整本地候选库放入源码仓库。Regular Git rejects files over 100 MiB; omit raw ZIPs, caches and local candidate banks. |
| [Repository licensing](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) | 根目录MIT覆盖工具代码；原创内容单独CC BY 4.0；第三方资料不擅自改授许可。MIT for code, CC BY 4.0 for original content; no relicensing of third-party material. |
| [File upload secret protection](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository) | 检查常见令牌、私钥、环境文件、私人路径；本地检查不能保证发现所有秘密。Check common token/private-key patterns, environment files and personal paths; local scanning is not exhaustive. |
| [Pages unpublishing](https://docs.github.com/en/pages/getting-started-with-github-pages/unpublishing-a-github-pages-site) | 保留网页开发能力，但移除可运行Pages部署工作流、不启用Pages、不上传网页构建产物。Keep local web development, remove active Pages workflow, do not enable Pages or distribute rendered website artifacts. |

## 本次发布范围 / Proposed public scope

源码、测试、中英文说明、来源与局限性、4道原创法规练习、JSON静态接口、离线笔记、发布工具。
Source, tests, bilingual guides, provenance/limitations, four original practice questions, static JSON, offline notes and release tooling.

用户导入包及合并库（3765道独立题，3573道内容完整）只作为本地调查资料，
未确认上游题干/解析/图片的完整授权链，因此不进入本次公开包。
The supplied archive and merged bank remain local: upstream redistribution rights have not been established for all question text, explanations and images.
内容完整不等于答案最新或拥有再分发权。A complete record does not establish current correctness or redistribution rights.

## 发布门槛 / Publication gate

1. 生成并查看源码ZIP、离线笔记ZIP、API ZIP及SHA256SUMS。Inspect source/vault/API archives and hashes.
2. 查看PUBLICATION-MANIFEST.json和文件清单，确认无本地候选题库、账号秘密或个人学习进度。Inspect the manifest and file list; omit local banks, credentials and learner progress.
3. 在GitHub确认登录账号、仓库名和可见性。Verify account, repository name and visibility.
4. 得到用户对该具体包及仓库的明确确认后，才能创建仓库、上传或发布Release。Obtain explicit approval of the exact package and destination before creating/uploading/publishing.
5. 上传后核对文件、提交、Release附件和可下载性；确认Pages未启用。Verify repository contents, commit, release assets/downloads and that Pages remains disabled.

不包含在包中的文件不会因为.gitignore而自动获得保护；实际发布以白名单生成目录为准。
.gitignore alone does not protect a browser upload; upload only the allowlisted publication directory.
