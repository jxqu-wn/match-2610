"""Offline routing experiments. No workspace changes, no external dependencies."""
import collections
import csv
import importlib.util
import json
import math
from pathlib import Path
import random
import re
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/database_routing/linear'
OUT.mkdir(parents=True, exist_ok=True)


def label(row):
    return '|'.join(sorted(set(row[k] for k in ('db', 'db1', 'db2', 'db3') if k in row)))


def features(text):
    text = re.sub(r'\s+', '', text.lower())
    return collections.Counter(text[i:i+n] for n in (1, 2, 3)
                               for i in range(len(text)-n+1))


class Model:
    def __init__(self, rows):
        self.rows = rows
        self.labels = sorted(set(map(label, rows)))
        self.counts = [features(row['question']) for row in rows]
        df = collections.Counter(t for c in self.counts for t in c)
        self.idf = {t: math.log((len(rows)+1)/(n+1))+1 for t,n in df.items()}
        self.postings = collections.defaultdict(list)
        self.vectors = []
        self.nb = {c: collections.Counter() for c in self.labels}
        for i,(row,count) in enumerate(zip(rows,self.counts)):
            vector = self.vector(count)
            self.vectors.append(vector)
            for t,w in vector.items():
                self.postings[t].append((i,w))
            self.nb[label(row)].update(count)
        self.totals = {c:sum(count.values()) for c,count in self.nb.items()}
        self.weights = {c:collections.defaultdict(float) for c in self.labels}
        rng = random.Random(42)
        order = list(range(len(rows)))
        for epoch in range(12):
            rng.shuffle(order)
            for i in order:
                vector = self.vectors[i]
                scores = self.linear_scores(vector)
                truth = label(rows[i])
                other = max((c for c in self.labels if c != truth), key=scores.get)
                if scores[truth] - scores[other] < 1:
                    step = min(0.3, (1-scores[truth]+scores[other])/2)
                    for t,w in vector.items():
                        self.weights[truth][t] += step*w
                        self.weights[other][t] -= step*w

    def vector(self, counts):
        v = {t:(1+math.log(n))*self.idf[t] for t,n in counts.items() if t in self.idf}
        norm = math.sqrt(sum(w*w for w in v.values())) or 1
        return {t:w/norm for t,w in v.items()}

    def linear_scores(self, vector):
        return {c:sum(w*self.weights[c].get(t,0) for t,w in vector.items()) for c in self.labels}

    def predict_all(self, question):
        counts = features(question)
        vector = self.vector(counts)
        similarity = collections.defaultdict(float)
        for t,w in vector.items():
            for i,value in self.postings[t]:
                similarity[i] += w*value
        neighbors = sorted(similarity, key=similarity.get, reverse=True)[:9]
        predictions = {}
        if not neighbors:
            return {name:'unknown' for name in ('nearest','vote3','vote5','nb','linear','hybrid')}
        predictions['nearest'] = label(self.rows[neighbors[0]])
        for k in (3,5):
            votes = collections.Counter()
            for i in neighbors[:k]:
                votes[label(self.rows[i])] += similarity[i]**3
            predictions[f'vote{k}'] = max(votes,key=votes.get)
        nb_scores = {c:sum(n*math.log((self.nb[c].get(t,0)+0.1)/
                                    (self.totals[c]+0.1*len(self.idf)))
                          for t,n in counts.items() if t in self.idf) for c in self.labels}
        predictions['nb'] = max(nb_scores,key=nb_scores.get)
        scores = self.linear_scores(vector)
        predictions['linear'] = max(scores,key=scores.get)
        votes = collections.Counter()
        for i in neighbors[:5]:
            votes[label(self.rows[i])] += similarity[i]**3
        total = sum(votes.values()) or 1
        hybrid = {c:scores[c]+0.8*votes[c]/total for c in self.labels}
        predictions['hybrid'] = max(hybrid,key=hybrid.get)
        return predictions


def evaluate(model, rows):
    predictions = [model.predict_all(row['question']) for row in rows]
    return {name:sum(p[name]==label(r) for p,r in zip(predictions,rows))/len(rows)
            for name in predictions[0]}, predictions


def main():
    start = time.time()
    train = json.loads((ROOT/'data/赛题8/splits/train.json').read_text())
    validation = json.loads((ROOT/'data/赛题8/splits/validation.json').read_text())
    groups = collections.defaultdict(list)
    for row in train:
        groups[label(row)].append(row)
    rng = random.Random(2026)
    fit,dev = [],[]
    for key in sorted(groups):
        rows = groups[key][:]
        rng.shuffle(rows)
        n = max(1,round(len(rows)*0.1))
        dev.extend(rows[:n]); fit.extend(rows[n:])
    print('Training internal development models...', flush=True)
    model = Model(fit)
    dev_metrics,_ = evaluate(model,dev)
    # Select only from an internal split of training data; validation remains untouched.
    selected = max(dev_metrics,key=dev_metrics.get)
    print(json.dumps({'internal_dev':dev_metrics,'selected':selected}),flush=True)
    print('Training selected model on full training split...',flush=True)
    model = Model(train)
    metrics,predictions = evaluate(model,validation)
    chosen = [p[selected] for p in predictions]
    details = [dict(question_id=r['question_id'], question=r['question'],
                    expected=label(r), predicted=p, correct=p==label(r))
               for r,p in zip(validation,chosen)]
    grouped = {}
    for key in sorted(set(map(label,validation))):
        subset = [r for r in details if r['expected']==key]
        grouped[key] = {'count':len(subset),'correct':sum(r['correct'] for r in subset),
                        'accuracy':sum(r['correct'] for r in subset)/len(subset)}
    # Repeated samples are diagnostics, not independent validation observations.
    random_rates,balanced_rates = [],[]
    for seed in range(1000):
        rng = random.Random(seed)
        sample = rng.sample(details,20)
        random_rates.append(sum(r['correct'] for r in sample)/20)
        balanced = []
        for key in sorted(grouped):
            balanced += rng.sample([r for r in details if r['expected']==key],4)
        balanced_rates.append(sum(r['correct'] for r in balanced)/20)
    def summarize(rates):
        return {'runs':len(rates),'mean':sum(rates)/len(rates),'min':min(rates),
                'max':max(rates),'at_least_90_percent':sum(r>=0.9 for r in rates),
                'strictly_above_90_percent':sum(r>0.9 for r in rates)}
    summary = {'train_size':len(train),'internal_dev_size':len(dev),
               'validation_size':len(validation),'internal_dev_metrics':dev_metrics,
               'selected_method':selected,'validation_accuracy':metrics[selected],
               'validation_correct':sum(r['correct'] for r in details),
               'by_database':grouped,'random20':summarize(random_rates),
               'balanced20':summarize(balanced_rates),'elapsed_seconds':time.time()-start}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    (OUT/'validation_predictions.json').write_text(json.dumps(details,ensure_ascii=False,indent=2))
    (OUT/'errors.json').write_text(json.dumps([r for r in details if not r['correct']],ensure_ascii=False,indent=2))
    (OUT/'split_ids.json').write_text(json.dumps({'fit':[r['question_id'] for r in fit],
                                               'dev':[r['question_id'] for r in dev]},indent=2))
    with (OUT/'sampling.csv').open('w') as f:
        writer=csv.writer(f); writer.writerow(['seed','random20','balanced20'])
        writer.writerows(zip(range(1000),random_rates,balanced_rates))
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    main()
