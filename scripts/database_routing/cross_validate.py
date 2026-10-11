import collections
import json
import random
import time
from experiment import Model, ROOT, OUT, label

start = time.time()
train = json.loads((ROOT/'data/赛题8/splits/train.json').read_text())
groups = collections.defaultdict(list)
for i,row in enumerate(train):
    groups[label(row)].append(i)
folds = [[] for _ in range(5)]
rng = random.Random(42)
for key in sorted(groups):
    rng.shuffle(groups[key])
    for j,i in enumerate(groups[key]):
        folds[j % 5].append(i)
details=[]
fold_metrics=[]
for fold,indices in enumerate(folds):
    excluded=set(indices)
    questions={train[i]['question'] for i in indices}
    fit=[r for i,r in enumerate(train) if i not in excluded and r['question'] not in questions]
    model=Model(fit)
    correct=0
    for i in indices:
        row=train[i]
        vector=model.vector(__import__('experiment').features(row['question']))
        scores=model.linear_scores(vector)
        prediction=max(scores,key=scores.get)
        ok=prediction==label(row)
        correct+=ok
        details.append(dict(question_id=row['question_id'],question=row['question'],
                            expected=label(row),predicted=prediction,correct=ok,fold=fold))
    fold_metrics.append(dict(fold=fold,fit_count=len(fit),test_count=len(indices),
                             correct=correct,accuracy=correct/len(indices)))
    print(json.dumps(fold_metrics[-1]),flush=True)
rates=[]
balanced=[]
for seed in range(1000):
    rng=random.Random(seed)
    rates.append(sum(r['correct'] for r in rng.sample(details,20))/20)
    selected=[]
    for key in sorted(groups):
        selected+=rng.sample([r for r in details if r['expected']==key],4)
    balanced.append(sum(r['correct'] for r in selected)/20)
def summary(values):
    return dict(runs=len(values),min=min(values),mean=sum(values)/len(values),
                at_least_90_percent=sum(v>=0.9 for v in values),
                strictly_above_90_percent=sum(v>0.9 for v in values))
report=dict(count=len(details),correct=sum(r['correct'] for r in details),
            accuracy=sum(r['correct'] for r in details)/len(details),folds=fold_metrics,
            random20=summary(rates),balanced20=summary(balanced),
            elapsed_seconds=time.time()-start)
(OUT/'cross_validation_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(OUT/'cross_validation_predictions.json').write_text(json.dumps(details,ensure_ascii=False,indent=2))
(OUT/'cross_validation_errors.json').write_text(json.dumps([r for r in details if not r['correct']],ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
