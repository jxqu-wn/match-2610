# 数据库分类

三个方案共用 `data/赛题8/splits` 下的数据划分，输出数据库系统集合及 single/multi。未实现 SQL 生成、业务库覆盖验证或跨库执行顺序。

本次验证：GPU FP16 embedding＋逻辑回归为 99.83%（582/583），原 CPU int8 实验为 98.97%（577/583），字符线性分类器为 100%（583/583）；11 项单元测试通过。详见 [测试记录](RESULTS.md)。

| 文件 | 功能 |
|---|---|
| route_question.py | 原字符二元组检索基线，附带 schema/知识证据 |
| experiment.py | 原字符 1～3 元组线性分类器，以及内部开发集方案比较 |
| route.py | 原字符线性分类器命令行 |
| cross_validate.py | 原字符方案五折交叉验证 |
| evaluate_clean.py | 原字符方案排除同文本后的验证 |
| embedding_classifier.py | 本地 Qwen 语义向量、分类训练、验证、预测 |
| test_*.py | 单元测试 |

原 `/tmp/database-routing-iteration` 中的线性分类代码已复制到本目录，并将项目根目录改为相对脚本推导；原临时实验记录保留。项目原有的两个路由文件已移动至此。

## 环境

在项目根目录执行：

```bash
uv venv .venv --python python
uv pip install --python .venv/bin/python -r scripts/database_routing/requirements.txt --index-url https://pypi.org/simple --index https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match
```

本次环境为 Python 3.14，项目 .venv 已安装 CUDA 版 PyTorch；依赖版本固定在 requirements.txt。模型已下载到 `models/Qwen3-Embedding-0.6B`，推理使用 `local_files_only=True`，不会再次下载模型。

## Embedding 方法

问题统一添加英文数据库路由指令，通过 Qwen3-Embedding-0.6B 编码。使用左侧 padding、最后一个有效 token 的隐藏状态和 L2 归一化，生成 1024 维向量。默认最大长度 256 token；超过该长度会截断。CPU 可通过 `--int8` 对 Linear 层使用动态量化，嵌入层保持 fp32；量化结果不等同于全精度结果，应分别评估。

仅从训练集内部开发集选择 k=1/3/5 的余弦近邻分类，或 C=0.1/1/10/100 的逻辑回归。开发集与训练集排除重复文本；独立验证集的同文本训练记录也排除。模型参数选择不使用验证标签。Embedding 模型冻结，不做微调。

```bash
.venv/bin/python scripts/database_routing/embedding_classifier.py evaluate --int8
.venv/bin/python scripts/database_routing/embedding_classifier.py predict --int8 --question '查询所有大型医院中拥有ICU的医院的名称。'
```

`predict` 必须在 `evaluate` 之后运行，并保持模型路径、量化方式、最大长度等设置一致。`--output` 可指定独立实验输出目录。

### GPU 推理

默认仍使用 CPU。GPU 环境需安装与本机驱动兼容的 CUDA 版 PyTorch；上面的 CPU 安装命令无法启用 GPU。可以先运行 `.venv/bin/python -c "import torch; print(torch.__version__, torch.cuda.is_available())"` 检查。

本机 RTX 4060、驱动 615.71.09（CUDA 13.3）使用以下命令安装 CUDA 13.0 版 PyTorch，其余依赖保持 requirements.txt 的版本：

```bash
uv pip install --python .venv/bin/python 'torch==2.14.1' --index-url https://download.pytorch.org/whl/cu130 --reinstall-package torch
```

安装后不要再次执行上面的 CPU 安装命令，否则可能替换 CUDA 版 PyTorch。

```bash
.venv/bin/python scripts/database_routing/embedding_classifier.py evaluate --device cuda:0 --dtype float16 --batch-size 16 --output outputs/database_routing/embedding_gpu
.venv/bin/python scripts/database_routing/embedding_classifier.py predict --device cuda:0 --dtype float16 --output outputs/database_routing/embedding_gpu --question '哪个国家培养的冰球运动员最多？'
```

`--device` 支持 cpu、auto、cuda、cuda:N；auto 在 CUDA 可用时使用 GPU，否则回退 CPU。`--dtype auto` 在 CPU 使用 float32，在 GPU 使用 float16，也可显式指定 float32 或硬件支持的 bfloat16。`--int8` 仅支持 CPU，与显式 CUDA 冲突时会报错；auto 配合 int8 会选 CPU。显存不足时降低 batch-size。

GPU 只加速 embedding 模型推理，近邻和逻辑回归仍在 CPU 上运行。输出向量以 float32 归一化并传回 CPU 保存。GPU 缓存按设备类型和精度隔离，原 CPU 缓存保持兼容；切换 CPU/GPU 或精度后需要重新 evaluate，建议分别指定输出目录，避免覆盖分类器和报告。GPU 编号不参与缓存键，同一精度可在不同 GPU 编号间使用。

评估同时重新运行字符线性分类器作为相同数据条件下的对照。报告保存至 `outputs/database_routing/embedding/summary.json`，逐题预测在 `predictions.json`，错误题在 `errors.json`，开发集选择在 `split_ids.json`。已缓存向量不会重复编码；缓存键包含模型文件信息、指令和推理设置。

单类/多类来自预测数据库集合大小；准确率按数据库集合完全匹配计算，不考察查询顺序。分类为闭集预测，不提供分布外拒答或概率可靠性保证。随机划分中的近似模板可能使结果偏高，不能据此保证未知问题准确率。

## 测试和字符方案复现

```bash
.venv/bin/python -m unittest discover -s scripts/database_routing -p 'test_*.py'
python scripts/database_routing/route.py '统计船舶总数'
python scripts/database_routing/experiment.py
python scripts/database_routing/cross_validate.py
python scripts/database_routing/evaluate_clean.py
```

字符方案仅依赖标准库，输出写入 `outputs/database_routing/linear`。
