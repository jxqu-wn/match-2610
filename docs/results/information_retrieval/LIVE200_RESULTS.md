# 全新200题验证：库表覆盖与相关性排名

2026-10-11。当前流程system-table-v2：系统类型分类→跨业务库检索表→LLM选择表/字段。DeepSeek模型为deepseek-flash。固定随机种子2026101102，重新抽取200题，排除此前70个不同测试题及与训练问题规范化后重复的题目。系统类型来自仅训练集训练的保存分类器，不用参考系统标签做推理。

系统类型完全正确199/200（99.5%）。参考SQL仅用于生成完成后的本地评分；不进入检索、上下文、补检索请求或外部模型。

## 全部参考库/表覆盖

业务库是表所属的逻辑业务命名空间，不是MYSQL/SQLite等系统类型。完整覆盖要求每题的全部参考对象均包含于对应集合，允许额外候选。

| 阶段 | 全部参考业务库覆盖 | 全部参考表覆盖 |
|---|---:|---:|
| 首轮提供上下文 | 199/200（99.5%） | 193/200（96.5%） |
| 补检索后提供上下文 | 199/200（99.5%） | 196/200（98.0%） |
| 模型最终选择 | 189/200（94.5%） | 176/200（88.0%） |

最终所选业务库集合完全一致180/200（90.0%），表集合完全一致155/200（77.5%）。最终业务库由所选表的归属计算，不是独立业务库路由结果。

## 相关性排名口径

表排名：原始问题在预测系统范围内的全部schema按关键词与embedding的RRF融合分数排序；多系统合并计算此诊断排名。主流程仍按系统轮流配额召回，因此该排名不等于实际上下文顺序。排名发生在外键扩展、案例提升和补检索之前。

业务库排名：取库内最高表RRF分数作为库分数，降序排列；同分按业务库ID。这是诊断时由表相关性归并的排名，当前系统没有独立的业务库相关性模型，不表示LLM业务库置信度。

每道题的每个不同参考库/表计一次，同一对象跨题重复计数。均值与分位数在有排名的对象上计算；系统分类范围外的参考对象标为无排名，不作为0，不偷偷计入Top-K。

| 对象 | 参考出现次数 | 有排名次数 | 平均排名 | 中位数 | P90 | P95 | 最大排名 | 无排名次数 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 参考业务库 | 217 | 215 | 1.19 | 1 | 2 | 2 | 3 | 2 |
| 参考表 | 381 | 379 | 4.33 | 2 | 7 | 14 | 92 | 2 |

若先对每题参考对象的排名取均值，再对各题平均：参考业务库为1.17，参考表为3.39。完全无排名的题目不进入这一均值。

## 排名分布

| 排名区间 | 参考业务库次数（占全部参考库次数） | 参考表次数（占全部参考表次数） |
|---|---:|---:|
| 1 | 175（80.65%） | 153（40.16%） |
| 2-3 | 40（18.43%） | 127（33.33%） |
| 4-6 | 0（0.00%） | 54（14.17%） |
| 7-8 | 0（0.00%） | 11（2.89%） |
| 9-12 | 0（0.00%） | 11（2.89%） |
| 13-20 | 0（0.00%） | 8（2.10%） |
| 21+ | 0（0.00%） | 15（3.94%） |
| 无排名 | 2（0.92%） | 2（0.52%） |

| 累计范围 | 参考业务库命中比例 | 参考表命中比例 | 全题全部参考库在范围内 | 全题全部参考表在范围内 |
|---|---:|---:|---:|---:|
| Top-1 | 80.65% | 40.16% | 159/200（79.5%） | 57/200（28.5%） |
| Top-3 | 99.08% | 73.49% | 199/200（99.5%） | 136/200（68.0%） |
| Top-6 | 99.08% | 87.66% | 199/200（99.5%） | 165/200（82.5%） |
| Top-8 | 99.08% | 90.55% | 199/200（99.5%） | 171/200（85.5%） |
| Top-12 | 99.08% | 93.44% | 199/200（99.5%） | 178/200（89.0%） |
| Top-20 | 99.08% | 95.54% | 199/200（99.5%） | 185/200（92.5%） |

## 实际提供上下文的位置与噪声

该位置包含外键、案例提升、补检索追加，仅作为补充，不与上面的原始相关性排名混用。
已提供参考表376次，平均上下文位置2.67，中位数2，P95为8，最大9。未提供的参考表不进入位置均值，但已计入覆盖缺失。
上下文累计候选表1430次，其中参考表命中376次，非参考候选1054次（73.71%）。非参考不直接等于无用资料。

## 首轮漏表与最终未覆盖题

| 题号 | 首轮缺少参考表 | 补检索后仍缺少参考表 | 最终选择缺少参考表 |
|---|---|---|---|
| 6203 | SQLite:movie_3.actor | 无 | 无 |
| 3404 | SQLite:soccer_2016.Country | 无 | SQLite:soccer_2016.City、SQLite:soccer_2016.Country、SQLite:soccer_2016.Match、SQLite:soccer_2016.Venue |
| 3432 | SQLite:soccer_2016.Team | SQLite:soccer_2016.Team | SQLite:soccer_2016.Team |
| 3366 | SQLite:soccer_2016.Team | 无 | 无 |
| 220 | MYSQL:common.vessel_type_dict、MYSQL:transportation.vessel | MYSQL:common.vessel_type_dict、MYSQL:transportation.vessel | MYSQL:common.vessel_type_dict、MYSQL:transportation.vessel |
| 1643 | MYSQL:education_2024.student | MYSQL:education_2024.student | MYSQL:education_2024.student |
| 1696 | MYSQL:education_2024.course | MYSQL:education_2024.course | MYSQL:education_2024.course、MYSQL:education_2024.enrollment、MYSQL:education_2024.student |

最终选择未覆盖全部参考业务库题号：1622、4204、4248、1789、3404、5345、220、3934、4465、1696、1914。
最终选择未覆盖全部参考表题号：1622、4204、4789、5148、4571、4248、4979、1789、3106、4765、4916、3404、3432、4981、3786、1037、5345、220、3934、1643、4465、4985、1696、1914。

## 模型调用、预算与隔离

状态：{"ready_with_assumptions": 93, "ready": 101, "error": 6}。错误/未决题保留在200题分母中，不删除失败样本。表集合覆盖或完全一致不代表字段、SQL或语义正确率。
真实API调用216次，输入1,381,332、输出51,134、总计1,432,466 token，平均每题7,162.3。调用目的分布：{"judgment": {"calls": 203, "input_tokens": 1283906, "output_tokens": 46482}, "repair": {"calls": 13, "input_tokens": 97426, "output_tokens": 4652}}。
证据裁剪题数0；输出长度终止0次。单次输入P95=9194，最大=11349。
索引5247条训练案例逐条核验，训练/验证题号交集0。最终上下文使用734个不同训练案例，全部属于训练子集。所选200题与此前70题交集为0。

产物位于outputs/information_retrieval/live200_rollback_v2：selection.json、excluded_previous.json、leakage_audit.json、prepared_*.json、question_*.json、report.json、coverage_report.json；后者包含逐题相关性排名与精确排名频数。

```bash
.venv/bin/python scripts/information_retrieval/test_live.py --sample-size 200 --random-seed 2026101102 --exclude-selection outputs/information_retrieval/live200_rollback_v2/excluded_previous.json --predicted-routing --output-directory outputs/information_retrieval/live200_rollback_v2
.venv/bin/python scripts/information_retrieval/review_coverage.py outputs/information_retrieval/live200_rollback_v2
```

低排名参考表逐项原因与证据见 [LIVE200_RANK_ANALYSIS.md](LIVE200_RANK_ANALYSIS.md)。
