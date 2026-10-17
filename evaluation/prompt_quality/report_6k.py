"""Render audited 6k experiment artifacts without reading API credentials."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def rate(value, n):
    return f'{value}/{n} ({value/n:.2%})' if n else '0/0'


def render(root):
    out = root / 'inference'
    comparison = read(out / 'comparison.json')
    selection = read(out / 'selection.json')
    audit = read(out / 'fact_fidelity_audit.json')
    if set(comparison) != set(audit) or any(r['fact_fidelity_errors'] for r in audit.values()):
        raise ValueError('Require complete, passing source-fidelity audit')
    names = selection['configurations']
    semantic_path = out / 'sql_evaluation/semantic_summary.json'
    quality_note = ('本轮小样本SQL复核未证明该配置总体更优；推荐依据仅为库表覆盖。'
                    if semantic_path.exists() else 'SQL质量对比完成前，此建议仅代表程序指标优先。')
    targets = read(root / 'private_evaluation/targets.json')
    split = read(root / 'public/partition.json')
    failure_stages = {}
    for name in names:
        cases = []
        for line in (out / 'runs' / name / 'prompts.jsonl').open():
            row = json.loads(line)
            qid = row['question_id']
            if qid not in split['tuning_ids']:
                continue
            target = targets[str(qid)]
            required = set(target['table_ids'])
            before = set(row['before_budget_table_ids'])
            after = {t['table_id'] for t in row['context']['candidate_tables']}
            if required - after:
                cases.append({'question_id': qid, 'topology': target['topology'],
                              'missing_route_engines': sorted(set(target['engines']) - set(row['context']['initial_databases'])),
                              'not_in_candidates': sorted(required - before),
                              'lost_by_budget': sorted((required & before) - after)})
        failure_stages[name] = cases
    (root / 'failure_stages.json').write_text(json.dumps(failure_stages, ensure_ascii=False, indent=2) + '\n')
    lines = ['# ≤6000 tokens 上下文参数实验', '',
             '6k指system及全部user/assistant历史消息的输入总量，不含生成输出。实验不修改生产默认预算。', '',
             '按完整库表覆盖优先，当前候选`quota_t8_k4_e0`：表候选8、全局knowledge4、案例0，Schema与knowledge各自BM25=50、embedding=50、RRF常数60、重排候选50；开启0.6B重排，沿用冻结路由。配合`compact/terse`序列化、独立全局知识候选保留及逐题6000输入预算裁剪。' + quality_note, '',
             f'服务器0.6B embedding与0.6B reranker完成{len(comparison)}组配置，每组284题；252题用于选参，12题作本轮开发验收，原20题作回归。已知7题属于开发诊断，包含在252题中。所有题此前用于开发，不属于独立测试集；无SQLite。', '',
             '## 选参结果', '',
             '|配置|选参完整库|选参完整表|部分正例knowledge ID命中|已审缺口ID命中|保守输入P95|',
             '|---|---:|---:|---:|---:|---:|']
    for name in names:
        r = comparison[name]
        t = r['tuning']
        lines.append(f"|{name}|{rate(t['complete_db'],t['count'])}|{rate(t['complete_table'],t['count'])}|{t['positive_knowledge_hits']}/{t['positive_knowledge_total']}|{r['reviewed_gap_hits']}/{r['reviewed_gap_total']}|{t['tokens_p95']:.0f}|")
    lines += ['', '完整表覆盖=参考查询需要的所有表均出现在最终提示词的题数/题数；完整库同理。knowledge只覆盖现有部分正例，不等于必要业务事实完整率，也不评价噪声。基线为旧流程强制适配6k后的结果，不代表旧21k预算的原成绩。', '',
              'knowledge18可保留8/8个已审知识缺口，却使完整表覆盖从248降到243；不宜简单增加知识条数。候选条数与最终入模条数须同时受总token预算控制。P95相差64 tokens以内且覆盖相同视为持平，优先保持匹配种子配置；没有依据把几个token的差异包装成质量提升。', '',
              '## 多表、多库单列', '', '|配置|单表|同业务库多表|同系统跨业务库|跨系统|', '|---|---:|---:|---:|---:|']
    for name in names:
        groups = comparison[name]['tuning_groups']
        cells = [rate(groups[g]['complete_table'], groups[g]['count']) for g in
                 ('single_table', 'same_business_multitable', 'same_system_cross_business', 'cross_system')]
        lines.append('|' + name + '|' + '|'.join(cells) + '|')
    lines += ['', '跨系统选参样本仅3题，比例不能外推到113道联邦测试题。', '',
              '## 分环节实验', '',
              '以下均为配对的单因素变化，只使用252题选参指标；高knowledge分支基线243，低knowledge分支基线248。', '',
              '|Schema参数|高knowledge完整表|低knowledge完整表|', '|---|---:|---:|',
              '|BM25/embedding候选50，RRF60，重排50|243|248|']
    for field, suffix in [('BM25候选25', 'bm25_top_k_25'), ('BM25候选100', 'bm25_top_k_100'),
                          ('embedding候选25', 'embedding_top_k_25'), ('embedding候选100', 'embedding_top_k_100'),
                          ('RRF常数20', 'rrf_k_20'), ('RRF常数100', 'rrf_k_100'),
                          ('重排候选25', 'rerank_top_k_25'), ('重排候选100', 'rerank_top_k_100'),
                          ('关闭重排', 'rerank_enabled_False')]:
        high = comparison['stage_schema_' + suffix]['tuning']['complete_table']
        low = comparison['lean_stage_schema_' + suffix]['tuning']['complete_table']
        lines.append(f'|{field}|{high}|{low}|')
    lines += ['', 'knowledge分支及案例分支调整未提高最高完整表覆盖；knowledge支持权重0/0.25/1与Schema扩路由也未带来提升。放开到全部引擎，高knowledge分支完整表降到219/252、完整库降到243/252，且明显增加重排计算，故沿用冻结路由。案例检索参数的覆盖结果持平，不能推断案例对最终SQL质量无作用。', '',
              '## 参数与预算', '',
              '固定system保守估算约1310 tokens。紧凑Schema保留全部列名/类型/可空性/注释和主外键，删除逐列重复的来源/审核元数据与检索调试信息；完整预算前对象另存。原文不摘要、不改写。', '',
              '候选数量是上限，不等于实际发给LLM的数量。先组装候选，再按全部消息预算裁剪；优先删除案例，再移除未受保护的低排名表，最后裁剪knowledge。额外Schema与修复历史也受6000输入估算限制，超限请求不会发送。', '',
              '|配置|候选表上限|knowledge上限|案例上限|实际平均表/知识/案例|', '|---|---:|---:|---:|---:|']
    for name in names:
        p = comparison[name]['parameters']
        a = audit[name]['average_counts']
        lines.append(f"|{name}|{p['tables']}|{p['knowledge']}|{p['examples']}|{a['tables']:.2f}/{a['knowledge']:.2f}/{a['examples']:.2f}|")
    lines += ['', '完整可复用配置见[recommended_parameters.json](recommended_parameters.json)，逐项配对变化见[stage_effects.json](stage_effects.json)。', '',
              '缺表按“路由未包含目标引擎”“目标表未进候选”“已召回但被预算删除”分别记录于[failure_stages.json](failure_stages.json)，同题可能存在多个原因。完整库覆盖不能替代完整表覆盖；跨年库配额实验没有进一步提升表覆盖。', '',
              '## 实验边界与审计', '',
              f"{sum(v['cases'] for v in audit.values())}份上下文通过原文保真与预算审计；字段、主外键、知识原文、训练问答和原始值域样例变更错误为0。审计证明保留内容忠实，不证明所有必要事实已召回。", '',
              '模型文档最大检索输入均小于512 tokens，提高embedding截断长度无实际收益。重排使用2048。模型缓存复用，部分分支并发；耗时不视为独立冷启动基准。', '',
              '原始Schema、knowledge、训练SQL中的缺失、歧义与冲突保留；不按验证题号插入表/知识，不把全局候选升级为已确认关联。单因素实验不覆盖所有参数交互，当前最优仅指已测配置。', '']
    token_path = out / 'provider_token_audit.json'
    if token_path.exists():
        token = read(token_path)
        lines += ['## DeepSeek输入长度验证', '',
                  f"实际完成{token['jobs']}个生成任务，共{token['calls']}次API调用；逐次usage.prompt_tokens最大{token['max_prompt_tokens']}，超过6000的调用{token['over_limit_calls']}，用量缺失{token['missing_usage_calls']}次。本地保守估算与服务端tokenizer并不相同。", '',
                  f"最终生成失败{len(token['generation_failures'])}个任务，均为旧基线：1853补充证据、3012修复未知字段后本地估算超限而停止。三个新方案各23/23通过静态结构/字段校验；没有因失败而追加更大预算重跑。", '']
    if semantic_path.exists():
        semantic = read(semantic_path)
        lines += ['## SQL生成对比', '',
                  '采用Codex静态业务语义复核，没有数据库执行，也没有独立人工或外部LLM裁判。业务核心满足数含仅精度/投影规则差异的答案；不能解释为完整提示词契约准确率。', '',
                  '|配置|本轮12题确认满足|固定8题子集确认满足|已知7题|旧回归4题|', '|---|---:|---:|---:|---:|']
        for name in names:
            results = semantic['results']
            cells = []
            for part, scope in [('generation_holdback', 'overall'), ('generation_holdback', 'fixed_source_resolved_subset'),
                                ('development_diagnostic', 'overall'), ('regression', 'overall')]:
                s = results[part][name][scope]
                cells.append(f"{s['confirmed_satisfies']}/{s['questions']}；未决{s['unresolved']}")
            lines.append('|' + name + '|' + '|'.join(cells) + '|')
        lines += ['', '固定来源未决题在生成前登记为566、1853、1919、2980。新出现的不确定性仍保留在固定8题分母中，避免按结果改变分母。逐题依据、规则问题和引用语句见[inference/sql_evaluation/semantic_reviews.json](inference/sql_evaluation/semantic_reviews.json)。', '']
        lines += ['四个方案固定8题均仅确认3题满足；低knowledge方案另有1题行政区划取值/层级未决。知识缺口题得到改善，并未在主验收子集中体现整体SQL提升，不能把98.41%的表覆盖解释为SQL准确率。', '',
                  '|配置|主验收同系统跨业务库|主验收跨系统|旧回归跨系统|', '|---|---:|---:|---:|']
        for name in names:
            groups = semantic['results']['generation_holdback'][name]['groups']
            old = semantic['results']['regression'][name]['groups']['cross_system']
            cells = [f"{s['confirmed_satisfies']}/{s['questions']}；未决{s['unresolved']}" for s in
                     (groups['same_system_cross_business'], groups['cross_system'], old)]
            lines.append('|' + name + '|' + '|'.join(cells) + '|')
        lines += ['', '两道主验收跨系统题中，2980自持力格式预先未决，2942四方案均存在轨迹算法错误；旧回归3012三个新方案均误把公司名称作为船舶输出。少量诊断案例不能外推到完整联邦测试集。', '',
                  '本轮14个已生成答案使用了提示词未提供的辅助表，仍通过基于全catalog的静态校验；另有字段正确但嵌套聚合、分母、粒度、几何算法错误。详细链路、原知识歧义及静态反例见[sql_quality_report.md](sql_quality_report.md)。', '']
    else:
        approval = root / 'external_transfer_approval_status.json'
        lines += ['SQL生成与静态语义复核尚未完成，不能仅凭覆盖率确定最终SQL质量。', '']
        if approval.exists():
            lines += ['本轮23题×4方案的92个任务、实际提示词已冻结；自动审批因之前的明确授权仅覆盖另一批27题/81次任务，拒绝本轮数据外发。等待本轮明确授权，尚无新API请求或服务端token统计。', '',
                      '实际提示词见[inference/sql_prompt_preview.json](inference/sql_prompt_preview.json)，全部23题分方案预览位于`inference/sql_prompt_previews/`。', '']
    (root / 'report.md').write_text('\n'.join(lines))
    print(json.dumps({'report': str(root / 'report.md'), 'configurations': len(comparison)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    render(p.parse_args().root)
