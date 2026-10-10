# 2026 全国大数据与计算智能挑战赛 · 赛题 8

赛题：面向多源异构数据源的统一查询指令生成。

## 资料

- [网页资料索引](docs/赛题8/网页资料/README.md)
- [赛题网页合集](docs/赛题8/网页资料/赛题网页合集.md)
- [训练集与验证集划分说明](data/赛题8/splits/README.md)

## 数据划分

原始训练集为 `data/赛题8/QA_train.json`。按验证集 10%、训练集 90%划分，使用固定随机种子 `42`，按单数据源类型及跨数据源查询方向分层抽样。

在项目根目录运行：

```bash
python scripts/split_dataset.py
```

脚本仅依赖 Python 标准库，生成训练集 `data/赛题8/splits/train.json`、验证集 `data/赛题8/splits/validation.json` 和划分清单 `data/赛题8/splits/split_manifest.json`。

模型训练和训练样例检索使用划分后的 `train.json`；`validation.json` 用于本地验证。官方 `QA_test.json` 用于竞赛预测。

## Git

远程仓库：<https://github.com/jxqu-wn/match-2610.git>
