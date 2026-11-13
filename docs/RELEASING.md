# 发布到自己的 GitHub

发布前先运行 prepare_publication.py，查看 release-bundles/ 下的源码、笔记、API压缩包及PUBLICATION-MANIFEST.json。
只上传 publish-ready/ 白名单目录；不要上传整个工作区。未经用户确认，不创建远端仓库、上传或发布Release。
网页版源码保留，但不部署、不启用Pages。确认应明确GitHub账号、仓库名、公开性和4道原创样例的实际内容范围。

1. 确认个人账号、仓库名（建议 jiakao-naoku）和公开可见性；核查数据许可及公开覆盖声明。
2. Python 3.11+ 执行 README 的完整检查流程；检查 ZIP 的笔记、图片、JSON 和许可。
3. 首次初始化 Git，提交源码、data、assets、docs、generated 和工作流。
4. 在自己的账号新建空仓库，连接 origin 并推送 main。不要携带任何账号令牌或候选题库缓存。
5. 本地与 Actions 检查通过后，将数据版本、变更记录和标签统一为 0.1.0 / v0.1.0。
6. 推送 v0.1.0 标签，Release 工作流会验证标签与数据版本一致，再上传两个 ZIP 和 SHA256SUMS。
7. 将 README 和调用方示例的 OWNER/REPO/TAG 替换为真实值；从新环境下载 ZIP 验证后再对外推荐。

后续版本：修改源数据和版本 → 核验 → 重建 generated → 测试 → 提交 → 新标签。
不移动已发布标签；修订使用新版本。发现答案错误或侵权内容时，先撤回对应公开内容并发布修复版本，
必要时删除受影响 Release 附件并说明原因。

GitHub Actions 须允许仓库的 GITHUB_TOKEN 写入 Releases；工作流只在标签推送时请求 contents:write。
pull request 和分支检查使用只读权限。
