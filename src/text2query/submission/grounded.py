"""Evidence-first Flash generation with fresh, bounded repair and review contexts.

Reference SQL and diagnostic test submissions are deliberately absent from this
module's inputs. The caller freezes the evidence pools before generation.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from ..io import canonical_json, file_sha256, read_json, sha256_text, write_json
from ..llm.client import ChatClient
from ..models import Catalog
from ..retrieval.sql_parser import SourceResolver
from .definition_dependencies import dependency_candidates
from .evidence import compact_table, knowledge_scope, schema_directory
from .generate import InputEstimator
from .integrity import validate_integrity
from .knowledge_spans import planning_item, resolve_annotations
from .packing import pack
from .source_rows import SourceRows
from .training_bindings import TrainingBindings

VERSION = "grounded-flash-v12"
COMMON = """你是数据库查询专家。仅依据用户问题、真实Schema、原始知识与原始字典值生成只读SQL/ES DSL。输出JSON对象。
证据优先级：题目明确要求、Schema结构/类型/原始字典、适用的口径规则与knowledge。训练案例仅是可能含错的弱证据，不能覆盖真实字段、字典或题目要求。知识中其他数据库的字段定义不可迁移到当前库。不要虚构地理边界、编码或连接条件。
区分同一数据库系统跨表/跨业务库和跨系统：MYSQL的不同业务库使用一条SQL连接；只有真实需求同时需要不同系统才使用两步。跨系统只允许db1/query1与db2/query2：第一步只输出一个键列，第二步用IN (result)接收其值列表，不能FROM/JOIN result。系统名只能MYSQL、POSTGRESQL、SQLite、Elasticsearch。SQL表名使用真实业务库或schema限定。
逐项核对：输出列和统计对象、每行代表的实体/时间粒度、过滤范围、分母总体、去重、防止一对多连接重复计数、排序与LIMIT。题目明确指定输出列时严格遵守，排序依据无需额外输出。不要用任意GROUP BY列改变统计粒度。
没有指定实体输出字段、地区维度的代码/名称或是否保留零计数时，参考同一主体、相同任务的原始训练输出用法，保留已有维度表示和输出形状；没有这种证据才选择最小合理表示。不能把“所有实体”自动理解为“所有物理字段”，也不能丢掉案例显示的实体标识维度。训练输出用法不能覆盖题目明确要求，不能借此移植案例过滤、年份、阈值或指标公式。先找到一组实体再统计“其”的指标时，区分逐实体统计与整体合计；没有明确要求合并总计，不应丢掉主体维度。固定的单一企业/日期条件不自动成为额外分组维度。
NULL表示未知，不等于0、否或空字符串。除非题目或原始资料明确规定缺失值视作0，不要给零值筛选加OR IS NULL，不要随意用COALESCE改变公式或过滤的语义。题目明确给出取值时，不擅自扩展为未经资料支持的英文码或同义值。比例默认分子除以分母，仅题目/知识明确要求百分数数值时才乘100。
知识被召回不代表全文适用。逐条核对知识的触发术语和限定语；例如仅描述某特定统计口径的条件，不得扩大为所有查询的默认过滤。不能因检索到公司经营状态、某类资质或例子，就给未要求它们的问题额外增加条件。题目明确指定某张表的记录数时，不得换成另一张关联表的行数。
definition_dependency_candidates是程序按已选知识原文提及的概念找出的原始定义候选，需独立核对适用范围。应用分支规则时要检查完整分支与判定条件，不能凭企业名称或常识假定某分支不可能命中；不存在资料支持的条件不能省略。
知识中关于许可证、部门或其他对象的分类，不自动成为企业、人员等所属主体的分类条件；不能把单向蕴含逆推为必要条件或等价定义。knowledge保留全文用于核查，applicability只是待核对的选段提示，不能越过全文的适用范围。不能截取分类口径内部的局部定义，将它扩大为所有未提及该分类的问题的通用条件；选末句时尤其要检查前文限定。需要不同片段时必须重新核对原题触发语，不能因企业称谓相近就追加持证、类型或状态限制。
原始训练语境可以提供业务称谓与实体表对应的弱证据：当已有案例直接用某实体表表示相同业务称谓、Schema又未给出更细的分类定义时，优先沿用已有实体范围，不能仅凭常识或字面相似度在经营类型等字段猜一个LIKE过滤。案例的年份、阈值、公式、输出列仍须逐项按本题核对，不照抄。
区分关联使用的内部主键与题目要输出的业务编号/名称；不要用内部ID替代业务标识。要求分别返回多个时期指标时，不要用跨期合计替代这些独立指标。原始字典或行政区划样本可能存在不统一的名称字段，按真实编码、层级与原文匹配范围，不能假定city_name精确等值总能覆盖所有下级区县。
对多个平行库作标量指标比较、要求返回各年指标时，优先一行多列输出这些指标；仅在题目要求按年分组列出时改为年份与指标多行。学期编号、学期代码、学年和年度分库是不同概念，不能在没有映射依据时互换或猜编码。按题目选定的实体集合计算总体，不能把缺失条件记为假设后直接忽略。
聚合和窗口计算分层：SUM(MAX(...))、SUM(LAG(...) OVER(...))在同一查询层不合法，应先在CTE/子查询计算，再在外层统计。使用AVG时区分按记录、按实体、按时间段的权重。比例确保非整数除法并处理零分母。
轨迹和空间查询区分“观察点在区域内”与“相邻轨迹线段穿过区域”；先按实体和时间构建所需完整轨迹，再执行轨迹空间判断，不能先删掉区外点改变轨迹。距离/长度使用正确单位、坐标系和支持的geometry/geography函数签名；不能把geometry专用谓词用于geography。至少N次观测需要显式计数约束，不能用DISTINCT替代。
行政范围根据已有区划层级/父级/编码及原始知识推导，市/省范围通常包含下级区县；节点精确等值与完整行政辖区不是一回事。原始字典的代码与中文标签是不同字段，不得把英文代码当成中文名称比较。使用已有地理边界原文，不能从城市名称臆测矩形。
如存在资料冲突或题目歧义，在uncertainties中如实记录并使用最有依据的解释；仍要满足所有明确要求。所需Schema缺失时返回need_more_evidence并列出目录中的table_ids。禁止伪造或忽略条件以得到非空结果。"""

PLANNING_COMMON = """你是数据库证据规划器，只选证据，不生成SQL。输出单个JSON对象。
题目明确要求与真实Schema优先，knowledge仅在适用范围内使用；原始训练案例是可能含错的弱证据，不能把其额外条件搬入本题。原文、字典值、字段、单位和业务库名称不可臆造，其他数据库的定义不能迁移。
MYSQL不同业务库可在同一条SQL连接；只有跨不同系统才需要两步单键值列表IN (result)。检索排名和外键只表示候选，不强制采用。规划必须核对输出形状、主体、过滤、时间、粒度与定义依赖。保持原始训练中有依据的输出惯例，但题目明确输出要求优先。
选知识片段时检查完整原文的限定范围，不能把分类专用定义变成通用条件；不能凭主体名称假定某税率或分类分支不可能命中。原文给出的本库特殊定义仍须按本库解释。"""

PLAN = """先制定证据计划，不输出SQL。表目录涵盖当前可用业务Schema，检索排名只供参考，路由不是限制。
逐项把输出、条件、粒度及关联需求映射到真实表；不要只因相似度高/存在外键就选择无关表。只选择确有必要的表，并检查是否缺少字典表、基础实体表或时间维表。
只选择真正用于本题的知识，逐条给出问题中实际出现的连续触发短语，以及原文source_fragments中的fragment_id列表。程序会取回原文，不要重写引文或使用省略号。定义与公式可选择多个片段，不能把有附加条件的知识当成无条件规则。计算指标时检查其定义、基础量、适用税率等依赖是否齐全；资料明确给出的本库特殊定义仍是本库依据。训练例仅用于识别类似问题的结构，不把例子条件搬到本题。
返回JSON：{"table_ids":["真实table_id"],"knowledge_applicability":[{"knowledge_id":原ID,"question_trigger":"问题原文连续短语","fragment_ids":["s1"],"use":"本题采用什么定义或公式"}],"requirements":[{"text":"明确要求","table_ids":[]}],"contract":{"output_layout":"逐列输出含义与行数形状","row_grain":"最终每行含义","population":"统计总体与分母","time_scope":"时间范围及对应真实字段","cross_system_required":false,"transfer_key":"跨系统时的键"},"uncertainties":[]}。"""

DRAFT = """根据全部证据完成查询。计划是可纠正的草案，不是权威结论。
返回JSON：{"status":"complete","answer":{"question_id":原ID,"db":"MYSQL","query":"真实SQL"},"requirements":[{"text":"逐项要求","implementation":"对应SQL片段"}],"uncertainties":[]}。
跨系统answer改用db1/query1、db2/query2，query2必须IN (result)。Elasticsearch query优先使用转义后的完整JSON字符串，避免多层DSL对象的大括号与answer层混淆；_source、size与query均属于同一个DSL根对象。
缺少Schema时返回{"status":"need_more_evidence","table_ids":["目录中的真实ID"],"reason":"缺少什么"}。不得输出Markdown。"""

REVIEW = """独立审查候选查询能否准确回答原始问题，不要沿用生成者的推理。
先从问题重新逐项核对输出、过滤、时间、统计粒度、分母、连接重复、编码/名称、空间语义和跨系统传值。用能暴露差异的小型反例检查候选，例如一对多、多次重复、零值和区外两点间穿越。
不因风格偏好修改可等价查询；发现实质缺陷才修正。不能以删除条件换取非空。缺少所需Schema时返回{"status":"need_more_evidence","table_ids":["目录中的真实ID"],"reason":"具体缺什么"}；不要凭字段名猜结构。
字段真实取值样本缺失不等于Schema缺失，不要反复索要已完整提供的表。不能取得样本时，按原始字段描述、知识和训练用法作最有依据的保守解释并在uncertainties报告；涉及混合单位时需明确单位判断，不忽略题目的单位要求。
返回JSON：{"status":"complete","verdict":"keep或repair","issues":[{"requirement":"问题要求","defect":"具体缺陷","evidence":"Schema/原始知识或SQL语义依据"}],"answer":完整最终提交对象,"uncertainties":[]}。"""

INTENT = """仅作原题的字面需求摘取，不写SQL，不引入训练案例或业务假设。逐字引用题目，再说明它明确要求的统计对象、输出项、条件、时间、粒度与排序。
不能因为某张表计数可能恒为1、某种统计通常更有意义，就把题目明确指定的表或主体换成关联表。没有在题目中出现的统计对象不能自行补出。不能把“分别返回多个时期的值”改成只返回合计。只说明未知事项，不替用户决定额外条件。
返回JSON：{"quoted_requirements":[{"quote":"题目中的连续原文","role":"output/counted_entity/filter/time/grain/sort"}]}。不要输出业务解释、概念展开、分类定义或猜测的unknowns；这些需要后续真实资料决定。"""


@dataclass(frozen=True)
class Profile:
    name: str
    planned: bool = False
    thinking: bool = False
    review: bool = False
    tables: int = 8
    knowledge: int = 12
    examples: int = 2
    input_limit: int = 16000
    output_limit: int = 12000
    reasoning_effort: str = "low"
    intent_first: bool = False


def system_prompt(rules: str, purpose: str) -> str:
    common = PLANNING_COMMON if purpose == PLAN else COMMON
    return common + "\n" + purpose + "\n以下为原始问题描述与查询口径规则，需结合其适用范围：\n" + rules


def knowledge_items(pool: dict, documents: dict, tables: dict, limit: int, selected: list[str] | None = None) -> list[dict]:
    namespaces = {tables[key].namespace.lower() for key in selected or [] if tables[key].namespace}
    output = []
    for hit in pool["knowledge"]:
        item = documents[hit["source_id"]]["data"]
        scope = knowledge_scope(item["knowledge_text"], tables)
        if not scope["eligible"]:
            continue
        declared = set(scope["declared_namespaces"])
        if namespaces and declared and not namespaces & declared:
            continue
        output.append({"source_id": hit["source_id"], **item})
        if len(output) >= limit:
            break
    return output


def weak_examples(pool, documents, selected, limit):
    output = []
    hits = list(pool.get("examples", [])[:1]) + list(pool.get("lexical_examples", [])) + list(pool.get("examples", [])[1:])
    seen = set()
    for hit in hits:
        if not limit or hit["source_id"] in seen:
            continue
        seen.add(hit["source_id"])
        document = documents[hit["source_id"]]
        if not document["table_ids"] or not set(document["table_ids"]) <= set(selected):
            continue
        data = document["data"]
        output.append({"source_id": hit["source_id"], "question": data["question"],
                       "steps": [{"engine": step["engine"], "query": step["query"]} for step in data["steps"]],
                       "status": "training_example_unverified; compare task differences before reuse"})
        if len(output) >= limit:
            break
    return output


def planning_messages(row, pool, documents, catalog, rules, source_rows=None, training_bindings=None, literal_intent=None):
    tables = catalog.by_id()
    payload = {"question_id": row["question_id"], "question": row["question"],
               "schema_directory": schema_directory(tables),
               "retrieved_table_candidates": [hit["table_ids"][0] for hit in pool["tables"]],
               "declared_fk_candidates_only": pool["fk_candidates"],
               "knowledge_candidates": [planning_item(item) for item in knowledge_items(pool, documents, tables, 48)]}
    seeds = [hit["table_ids"][0] for hit in pool["tables"][:8]]
    payload["retrieved_column_names"] = [{"table_id": key, "columns": tables[key].column_names} for key in seeds]
    payload["weak_training_examples"] = weak_examples(pool, documents, seeds, 2)
    if source_rows is not None:
        payload["source_row_evidence"] = source_rows.match(row["question"], knowledge_items(pool, documents, tables, 6))
    if training_bindings is not None:
        payload["training_literal_usage_unverified"] = training_bindings.match(row["question"])
        payload["training_case_scope_unverified"] = training_bindings.scope_examples(weak_examples(pool, documents, seeds, 6), limit=6)
    if literal_intent is not None:
        payload["literal_requirement_contract"] = literal_intent
    return [{"role": "system", "content": system_prompt(rules, PLAN)},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}]


def draft_messages(row, pool, documents, catalog, rules, profile, selected, plan=None, previous=None, errors=None, review=False, source_rows=None, training_bindings=None, literal_intent=None):
    tables = catalog.by_id()
    evidence = {"question_id": row["question_id"], "question": row["question"],
                "schema": [compact_table(tables[key]) for key in selected],
                "schema_directory": schema_directory(tables),
                "knowledge": knowledge_items(pool, documents, tables, 48 if plan is not None else profile.knowledge, selected)}
    if plan is not None:
        evidence["knowledge"] = resolve_annotations(plan.get("knowledge_applicability", []), evidence["knowledge"], row["question"])[:profile.knowledge]
        evidence["definition_dependency_candidates"] = dependency_candidates(
            evidence["knowledge"], knowledge_items(pool, documents, tables, 48, selected))
    if profile.examples and not review:
        evidence["weak_training_examples"] = weak_examples(pool, documents, selected, profile.examples)
    if source_rows is not None:
        evidence["source_row_evidence"] = source_rows.match(row["question"], evidence["knowledge"])
    if training_bindings is not None:
        evidence["training_literal_usage_unverified"] = training_bindings.match(row["question"])
        evidence["training_case_scope_unverified"] = training_bindings.scope_examples(
            weak_examples(pool, documents, selected, 6), limit=6)
    if literal_intent is not None:
        evidence["literal_requirement_contract"] = literal_intent
    if plan is not None and not review:
        evidence["draft_plan_may_be_corrected"] = {**plan, "knowledge_applicability": [
            {key: item[key] for key in ("knowledge_id", "question_trigger", "fragment_ids", "source_quote") if key in item}
            for item in plan.get("knowledge_applicability", []) if isinstance(item, dict)]}
    if previous is not None:
        evidence["candidate_answer"] = previous
    if errors:
        evidence["validation_errors"] = errors
    return [{"role": "system", "content": system_prompt(rules, REVIEW if review else DRAFT)},
            {"role": "user", "content": json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))}]


def normalized(answer):
    if isinstance(answer, dict):
        for suffix in ("", "1", "2"):
            if answer.get("db" + suffix) == "Elasticsearch" and isinstance(answer.get("query" + suffix), dict):
                answer["query" + suffix] = json.dumps(answer["query" + suffix], ensure_ascii=False, separators=(",", ":"))
    return answer


def generate(row: dict, pool: dict, documents: dict, catalog: Catalog, rules: str,
             profile: Profile, directory: Path, api_key: str, estimator: InputEstimator,
             extra_validator: Callable[[dict], list[str]] | None = None, source_rows: SourceRows | None = None,
             training_bindings: TrainingBindings | None = None) -> dict:
    signature = sha256_text(canonical_json({"version": VERSION, "profile": asdict(profile), "row": row,
                          "pool": pool, "catalog": catalog.model_dump(by_alias=True), "rules": rules,
                          "prompts": [COMMON, PLANNING_COMMON, PLAN, DRAFT, REVIEW, INTENT],
                          "extra_validator_enabled": extra_validator is not None,
                          "source_rows_sha256": source_rows.digest if source_rows is not None else None,
                          "client_code_sha256": file_sha256(Path(__file__).parents[1] / "llm/client.py"),
                          "training_literal_usage": training_bindings.match(row["question"]) if training_bindings is not None else [],
                          "candidate_documents": {hit["source_id"]: documents[hit["source_id"]]
                              for kind in ("knowledge", "examples", "lexical_examples") for hit in pool.get(kind, [])},
                          "code": {name: file_sha256(Path(__file__).with_name(name))
                                   for name in ("grounded.py", "integrity.py", "evidence.py", "source_rows.py", "training_bindings.py", "knowledge_spans.py", "projection_usage.py", "definition_dependencies.py", "packing.py")}}))
    path = directory / f"{row['question_id']}.json"
    run_attempt = 1
    if path.exists():
        old = read_json(path)
        if old.get("signature") != signature:
            raise ValueError("Run changed; use a new version directory")
        if old.get("answer"):
            return old
        run_attempt = old.get("run_attempt", 1) + 1
        write_json(directory / "attempt_history" / f"{row['question_id']}.{run_attempt - 1}.json", old)
    client = ChatClient(model="deepseek-flash", api_key=api_key, thinking=profile.thinking,
                        reasoning_effort=profile.reasoning_effort if profile.thinking else None,
                        timeout=300, retries=2, cache_dir=directory.parent / "api_cache",
                        default_headers={"Accept-Encoding": "identity"})
    trace = []
    tables = catalog.by_id()
    selected = [hit["table_ids"][0] for hit in pool["tables"][:profile.tables]]
    output = {"signature": signature, "row": row, "profile": asdict(profile), "trace": trace, "run_attempt": run_attempt,
              "generation_version": VERSION}

    def request(messages, purpose):
        messages = [dict(message) for message in messages]
        body = json.loads(messages[1]["content"])
        if run_attempt > 1:
            # Resume only failed cases within the same frozen run, without
            # replaying the same cached, structurally invalid plan indefinitely.
            body["retry_run_attempt"] = run_attempt
            messages[1]["content"] = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        complex_intent = re.search(r"比较|平均|比率|比例|占|费用|利润|税|率|轨迹|空间|距离|公里|半径|区域|附近|联查|跨|过去|最近|出现|各.+统计|(?:19|20)\d{2}.*(?:19|20)\d{2}", row["question"])
        multiple_engines = len({tables[key].engine for key in selected}) > 1
        complex_query = len(selected) >= 2 or complex_intent
        input_limit = (12000 if complex_intent else 6000) if purpose == "evidence_planning" else (profile.input_limit if complex_query or multiple_engines else 6000)
        if purpose == "literal_intent":
            input_limit = 6000
        messages, omitted = pack(messages, purpose, input_limit, estimator)
        estimate = estimator(messages)
        limit = min(profile.output_limit, 6000) if purpose == "evidence_planning" else min(profile.output_limit, 4000) if purpose == "literal_intent" else profile.output_limit
        limits = [limit, min(24000, limit * 2)] if profile.thinking else [limit]
        for output_limit in limits:
            item = {"purpose": purpose, "estimated_tokens": estimate, "input_limit": input_limit,
                    "messages": messages, "omitted_whole_evidence": omitted, "output_limit": output_limit}
            trace.append(item)
            client.reasoning_effort = ("low" if purpose in {"literal_intent", "evidence_planning"} else profile.reasoning_effort) if profile.thinking else None
            raw = client.complete(messages, output_limit, purpose)
            item["raw"] = raw
            item["call"] = client.calls[-1].as_dict()
            if client.calls[-1].finish_reason == "length" and output_limit != limits[-1]:
                continue
            if client.calls[-1].finish_reason not in {"stop", "cached"}:
                raise ValueError("Output truncated or stopped abnormally after bounded output expansion")
            try:
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise ValueError("Output must be JSON object")
                return value
            except ValueError as error:
                item["validation_errors"] = ["输出不是单个合法JSON对象：" + str(error)[:160]]
                return {"status": "invalid_json", "reason": item["validation_errors"][0]}
        raise ValueError("No completed output")

    try:
        literal_intent = None
        if profile.intent_first:
            intent_messages = [
                {"role": "system", "content": INTENT},
                {"role": "user", "content": json.dumps(row, ensure_ascii=False)},
            ]
            for intent_attempt in range(2):
                literal_intent = request(intent_messages, "literal_intent")
                quoted = literal_intent.get("quoted_requirements", [])
                if quoted and all(isinstance(item, dict) and isinstance(item.get("quote"), str)
                                  and item["quote"] and item["quote"] in row["question"] for item in quoted):
                    literal_intent = {"quoted_requirements": [{"quote": item["quote"], "role": item.get("role")}
                                                             for item in quoted],
                                      "status": "verbatim_question_spans; no_generated_business_meaning"}
                    break
                body = {**row, "repair": "逐条quote必须是原题连续原文，输出一个合法JSON对象，不改写引文", "attempt": intent_attempt + 1}
                intent_messages[1]["content"] = json.dumps(body, ensure_ascii=False)
            else:
                raise ValueError("Literal intent extraction must quote the original question exactly")
        plan = None
        if profile.planned:
            messages = planning_messages(row, pool, documents, catalog, rules, source_rows, training_bindings, literal_intent)
            for planning_attempt in range(3):
                plan = request(messages, "evidence_planning")
                proposed = list(dict.fromkeys(plan.get("table_ids", [])))
                validation_error = "Return one valid JSON object with only real directory table_ids"
                if proposed and len(proposed) <= 16 and all(key in tables for key in proposed):
                    try:
                        resolve_annotations(plan.get("knowledge_applicability", []), knowledge_items(pool, documents, tables, 48, proposed), row["question"])
                        break
                    except ValueError as error:
                        validation_error = str(error)
                body = json.loads(messages[1]["content"])
                body["planning_repair"] = {"attempt": planning_attempt + 1, "error": validation_error}
                messages[1]["content"] = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
            else:
                raise ValueError("Plan selected invalid table IDs")
            selected = proposed
        answer, errors = None, []
        review_pending = profile.review
        supplemented = False
        for attempt in range(6):
            if answer is not None and review_pending and not errors and (
                len(selected) >= 3 or re.search(r"比较|平均|比率|占比|退款率|成功率|轨迹|过去|最近|出现", row["question"])
            ):
                selected = list(dict.fromkeys(selected + [hit["table_ids"][0] for hit in pool["tables"][:8]]))[:16]
            messages = draft_messages(row, pool, documents, catalog, rules, profile, selected,
                                      plan, answer, errors, review=bool(answer is not None and review_pending and not errors),
                                      source_rows=source_rows, training_bindings=training_bindings, literal_intent=literal_intent)
            if errors:
                body = json.loads(messages[1]["content"])
                body["repair_attempt"] = attempt
                body["repair_instruction"] = "必须实际修改answer中的SQL或提交键，不能只在uncertainties声称已修正。不可假定另一个系统的表已被迁移。"
                messages[1]["content"] = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
            reviewing = answer is not None and review_pending and not errors
            value = request(messages, "independent_review" if reviewing else "draft" if attempt == 0 else "fresh_repair")
            if value.get("status") == "invalid_json":
                errors = [value["reason"]]
                continue
            if value.get("status") == "need_more_evidence":
                # Some responses mention the exact directory IDs only in their
                # reason/issues. Accept literal catalog IDs, never invent them.
                request_text = canonical_json(value)
                requested = list(value.get("table_ids", [])) + [key for key in tables if re.search(
                    r"(?<![a-zA-Z0-9_.])" + re.escape(key) + r"(?![a-zA-Z0-9_.])", request_text)]
                new = list(dict.fromkeys(key for key in requested if key in tables and key not in selected))
                if not new and not supplemented:
                    # A request for an already supplied table may actually mean
                    # missing metric definitions. Re-plan against the raw pool.
                    supplement = planning_messages(row, pool, documents, catalog, rules, source_rows, training_bindings, literal_intent)
                    body = json.loads(supplement[1]["content"])
                    body["evidence_request"] = value
                    body["knowledge_candidates"] = [planning_item(item) for item in knowledge_items(pool, documents, tables, 48, selected)]
                    supplement[1]["content"] = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
                    plan = request(supplement, "evidence_planning")
                    proposed = plan.get("table_ids", [])
                    if not isinstance(proposed, list) or not all(key in tables for key in proposed):
                        raise ValueError("Supplemental plan must select real directory table IDs")
                    revised = list(dict.fromkeys(selected + proposed))
                    if len(revised) > 16:
                        raise ValueError("Supplemental schema exceeds bounded evidence limit")
                    selected = revised
                    resolve_annotations(plan.get("knowledge_applicability", []), knowledge_items(pool, documents, tables, 48, selected), row["question"])
                    supplemented = True
                    continue
                if not new or len(selected + new) > 16:
                    if not new and supplemented and answer is not None and not errors:
                        # All real schemas and available knowledge have already
                        # been supplied. Preserve a previously validated draft
                        # rather than mislabel missing business values as schema
                        # errors. This is explicitly NOT a successful review.
                        output.update(answer=answer, supplied_table_ids=selected,
                                      review_status="unresolved_source_evidence",
                                      analysis={"status": "source_limited", "review_response": value,
                                                "uncertainties": [value.get("reason", "Source values/format remain unverified")]})
                        break
                    raise ValueError("Unresolvable evidence request after bounded knowledge supplementation")
                selected += new
                continue
            candidate = normalized(value.get("answer"))
            supplied_resolver = SourceResolver({key: tables[key] for key in selected})
            errors = validate_integrity(candidate, row, supplied_resolver)
            if isinstance(candidate, dict) and extra_validator is not None and not errors:
                errors.extend(extra_validator(candidate))
            trace[-1]["validation_errors"] = errors
            answer = candidate
            if errors:
                # If SQL names a real but unseen table, provide its original
                # schema before asking the model to regenerate a grounded SQL.
                global_resolver = SourceResolver(tables)
                if isinstance(candidate, dict):
                    from .validate import step_pairs
                    for db_key, query_key in step_pairs(candidate):
                        try:
                            refs = global_resolver.parse(candidate[query_key], candidate[db_key])["table_ids"]
                            selected += [key for key in refs if key not in selected]
                        except (KeyError, ValueError):
                            pass
                continue
            if reviewing:
                review_pending = False
            if not review_pending:
                output.update(answer=answer, analysis=value, supplied_table_ids=selected)
                break
        if "answer" not in output:
            raise ValueError("No valid reviewed answer within call budget")
    except Exception as error:  # noqa: BLE001 - persist a resumable failure
        output["error"] = f"{type(error).__name__}: {str(error)[:400]}"
    output["calls"] = [record.as_dict() for record in client.calls]
    if client.cache is not None:
        client.cache.close()
    write_json(path, output)
    return output
