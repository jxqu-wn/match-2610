"""Standalone classifier route; fitting reads only the training split."""
import argparse
import json
from experiment import Model, ROOT, features

parser=argparse.ArgumentParser()
parser.add_argument('question')
args=parser.parse_args()
if not args.question.strip():
    parser.error('问题不能为空')
train=json.loads((ROOT/'data/赛题8/splits/train.json').read_text())
model=Model(train)
scores=model.linear_scores(model.vector(features(args.question)))
prediction=max(scores,key=scores.get)
databases=prediction.split('|')
print(json.dumps(dict(question=args.question,query_type='single' if len(databases)==1 else 'multi',
                      databases=databases,method='character_ngram_linear_classifier',
                      note='输出为闭集分类结果；不表示字段覆盖或查询依赖已经验证。'),ensure_ascii=False,indent=2))
