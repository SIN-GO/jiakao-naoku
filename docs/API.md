# 静态 JSON 接口 v1

无后台服务、鉴权或动态查询 API。仓库路径为 `generated/api/v1/`；API ZIP 解压后为 `api/v1/`。
全部使用 UTF-8 JSON。schema_version 是接口结构版本，version 是数据发布版本。
破坏性结构变更将新增 v2；题目 ID 不随排序、文件位置或文字修订改变。

## 文件

- `manifest.json`：版本、核验基准日期、唯一题数、分片路径及数量、complete=false。
- `catalog.json`：车型、考点和允许发布的来源；附车型考试映射说明。
- `questions.json`：全部可发布题目；同一道题只有一条记录。
- `vehicles/{code}/{subject}.json`：对应车型、科目的题目数组。共用题跨分片出现，合并时按 ID 去重。
- `coverage.json`：每车型每科目收录/已核验/已发布数量、最近核验日期和缺口。

日期采用 YYYY-MM-DD。暂无核验日期为 null。两类科目的分片存在，不代表该车型必须参加两场考试。
不要依赖相邻记录的顺序，不要将目录已建立解释为题库已完整。

## 题目字段（导入与公开 JSON 使用相同形状）

| 字段 | 类型及含义 |
|---|---|
| id | 小写字母开头，小写字母/数字/短横线，2–80字符，稳定唯一 |
| subject | subject1 或 subject3_safe |
| vehicles | 适用车型代码数组；A1/A2/A3/B1/B2/C1–C6/D/E/F/M/N/P |
| kind | true_false / single / multiple |
| stem, explanation, reasoning, pitfall | 非空题干、解析、解题思路、易错点 |
| options | 大写单字母到选项文本的对象；判断题固定 A正确/B错误 |
| answers | 答案键数组；判断/单选1项，多选至少2项 |
| topics, sources | 非空考点ID、内容来源ID数组，必须已登记 |
| evidence | 答案依据数组，每项 source_id 和 locator（条号/段落） |
| images | 数组，可空；每项 path（assets内相对路径）、alt、license、source_id |
| origin | original_practice 或 source_question，不能把原创题标为真题 |
| license, version | 内容许可标识与题目修订版本，均非空 |
| rights_status | cleared / unknown / restricted |
| review_status | reviewed / pending / disputed |
| reviewed_at, reviewer | reviewed 时必填日期和核验者；必须如实注明 AI/人工 |
| review_note | 非空复核过程及局限性说明 |

仅 reviewed + rights_status=cleared 且全部内容及图片来源 redistribution=cleared 的题目导出。
evidence 可引用 reference_only 法规；这不授权复制法规页面中的图片或第三方解析。
版权争议记录即使答案已核验也不会导出。许可证是逐条描述，不由代码替代权利审查。
图片从 assets 复制到 vault/90-图片；程序加载图片时使用笔记包的该目录，JSON 不内嵌二进制。

来源必须包含 id/title/url/version/checked_at/redistribution，以及 stem_terms/explanation_terms/image_terms。
考点必须包含 id/title/summary。新增题目可参考仓库 data/questions.json 的完整实例。

## 固定版本调用

发布后将 OWNER、REPO 换成实际账号、仓库名，TAG 换成已发布标签（如 v0.1.0）。
不要把尚未创建的标签当作可用链接；固定标签优于跟随 main。

```python
import json
from urllib.request import urlopen
base = 'https://raw.githubusercontent.com/OWNER/REPO/TAG/generated/api/v1/'
with urlopen(base + 'manifest.json', timeout=30) as response:
    manifest = json.load(response)
part = next(p for p in manifest['partitions']
            if p['vehicle'] == 'C1' and p['subject'] == 'subject1')
with urlopen(base + part['path'], timeout=30) as response:
    questions = json.load(response)
print(manifest['version'], len(questions))
```

```javascript
const base = 'https://raw.githubusercontent.com/OWNER/REPO/TAG/generated/api/v1/';
async function read(path) {
  const response = await fetch(base + path);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
const manifest = await read('manifest.json');
const part = manifest.partitions.find(p => p.vehicle === 'C1' && p.subject === 'subject1');
const questions = await read(part.path);
console.log(manifest.version, questions.length);
```

GitHub Raw 为文件下载地址，不提供服务等级保证；生产调用建议缓存或下载 Release，并核对 SHA256SUMS。
