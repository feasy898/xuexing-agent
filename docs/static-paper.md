# 静态卷包（static paper）——生成、打印与纸面自诊

> 签署测试卡 TC-4（2026-10-08，裁定 D-1/D-5/D-6）。渠道裁定 = 静态卷文件优先：
> 本工具链把任意卷型一键装订成可离线分发的卷包。全程零网络、零数据回传。

## 1. 一键生成

```bash
.venv/bin/python tools/export_static_paper.py --spec-id spec_phy_jr_final --seed 42
# 输出目录默认 out/static_paper/<spec_id>_seed<seed>/（out/ 已 gitignore）
```

卷包六文件：

| 文件 | 内容 |
|---|---|
| `student.html` | 学生卷（A4 打印样式，自包含、零外链），卷头含 AI 标识与原创声明 |
| `student.txt` | 学生卷纯文本简版（同样的卷头文案） |
| `teacher.html` | 教师卷：逐题答案/解析/评分要点（仅教师面） |
| `kp_map.html` | 题号→KP 对照表 + 纸面自诊知识地图模板 |
| `answer_sheet.json` | OMR 答题卡（题号-选项映射，供 OMRChecker 对接） |
| `manifest.json` | 逐文件 sha256、逐题验证状态（dual/single）、难度配比与 `releasable` 判定 |

确定性：同一 `(spec_id, seed)` 重跑逐字节一致（无时钟、无随机）。

## 2. 打印

浏览器直接打开 `student.html` → 打印（A4，默认边距即可；渲染层自带
`@page` 分页与页码）。选择题选项竖排、解答题带作答框、填空带下划线。

## 3. 纸面自诊（不回传、不联网）

1. 学生作答后对照 `kp_map.html` 上半部分（题号→知识点对照表）找错题知识点；
2. 在下半部分「纸面自诊知识地图」把做错知识点的 ☐ 涂成 ☑；
3. 全程纸面完成，本工具链不采集、不存储任何作答数据。

## 4. 可发布判定（releasable）

`manifest.releasable = true` 当且仅当：

1. 卷内全部题目为双代理 agree 验证（`verification.agents≥2 且 answers_agree=true`）；
2. 成卷实际难度配比（basic/medium/hard 占比）与冷启动画像目标（海南 7:2:1）
   的每档偏差 ≤ **0.15**（冻结阈值，specs/drafts/static_paper.spec.md §4）。

只要含单代理验证题，学生卷与教师卷卷头都会加「内部样卷·未完成双代理复验」，
且 `releasable=false`——含单代理题的卷子一律不得对外分发。当前（2026-10-08）
全库双代理题占比低、且出卷按难度目标选题导致实际配比偏离 7:2:1，故现有
21 套卷型 `releasable` 均为 false——这是如实状态；双代理补验（TC-7/TC-8）
与发布索引（TC-5）按签署卡推进。

## 5. 对外发布判定（--verified-only 与发布索引）

```bash
.venv/bin/python tools/export_static_paper.py --spec-id <id> --verified-only
# 双代理 agree 题不足时逐大题打印 SHORTAGE，不产出可发布卷包，不降级凑题
.venv/bin/python tools/build_static_paper_index.py
# 生成 data/releases/static_paper_index_v0.json（21 条，RELEASABLE k 如实）
```

- `--verified-only` 只从「双代理 agree（verification.agents≥2 且
  answers_agree=true）」的题中选题；这是「可对外分发」的唯一题源口径。
- 发布索引 `data/releases/static_paper_index_v0.json` 逐卷型记录
  releasable 与逐大题缺口（section/form/need/have_verified），只能由
  `build_static_paper_index.py` 重建（确定性），禁止手改；TC-7/TC-8
  每批双代理回填后重跑，RELEASABLE 数随之如实增长。
- 2026-10-08 基线：RELEASABLE=0（双代理题存量尚未覆盖任何卷型的全部
  大题形态）——如实登记于 PM-STATE，作为 D-2 复议条件 (2) 的判据。

## 6. 校验门

```bash
.venv/bin/python tools/check_static_paper.py   # 21 套卷型逐套判定，末行 STATIC-PAPER-CHECK-OK
```

门内逐套断言九点：学生卷红线零违规；Σ题分=卷型总分；题号在学生卷/教师卷/
kp_map/答题卡/manifest 五处一致；kp_map 逐题 KP 对应；零外链零回传元素；
固定文案逐字在位且「真题」不出文案之外；单代理标签与 releasable 联动；
两次构建逐字节一致；manifest 哈希与画像版本自洽。

## 7. 视检样本

`docs/samples/static_paper/spec_phy_jr_final_seed42/` 为入库样本卷包
（spec_phy_jr_final × seed 42），可用 `tools/export_static_paper.py` 逐字节再生。
