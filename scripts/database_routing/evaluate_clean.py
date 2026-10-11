"""Evaluate frozen linear method with no identical validation text in training."""
import json
from experiment import Model, ROOT, OUT, label, features

p=ROOT/'data/赛题8/splits'
train=json.loads((p/'train.json').read_text())
validation=json.loads((p/'validation.json').read_text())
texts={r['question'] for r in validation}
fit=[r for r in train if r['question'] not in texts]
model=Model(fit)
rows=[]
for row in validation:
    scores=model.linear_scores(model.vector(features(row['question'])))
    prediction=max(scores,key=scores.get)
    rows.append(dict(question_id=row['question_id'],expected=label(row),
                     predicted=prediction,correct=prediction==label(row)))
summary=dict(training_size_after_excluding_validation_texts=len(fit),
             validation_count=len(validation),correct=sum(r['correct'] for r in rows),
             accuracy=sum(r['correct'] for r in rows)/len(rows))
(OUT/'deduplicated_validation_summary.json').write_text(json.dumps(summary,indent=2))
(OUT/'deduplicated_validation_predictions.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(summary,indent=2))
