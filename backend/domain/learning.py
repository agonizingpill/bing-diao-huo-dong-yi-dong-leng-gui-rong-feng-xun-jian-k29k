import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

POSITIVE = '确需换格'

def features(row):
    return [row['mass_kg'],row['melt'],row['drift']]

def score(source, pool, neighbors):
    train,held=pool[:-8],pool[-8:]
    if not 1<=neighbors<=len(train):
        raise ValueError('近邻数超出可训练基线')
    scale=StandardScaler().fit([features(row) for row in train])
    knn=NearestNeighbors(n_neighbors=neighbors).fit(scale.transform([features(row) for row in train]))
    def density(rows):
        distances=knn.kneighbors(scale.transform([features(row) for row in rows]))[0]
        return 1/(1+distances.mean(axis=1))
    return {'density':round(float(density([source])[0]),5),
            'threshold':round(float(np.quantile(density(held),.15)),5),
            'train':len(train),'held':len(held)}

def evaluate(data):
    stats={'samples':len(data['batch']),'miss_current':0,'miss_trial':0,
           'false_current':0,'false_trial':0}
    for item in data['batch']:
        pool=data['pools'][item['sample']['cell']]
        for side,neighbors in (('current',data['base']['neighbors']),
                               ('trial',data['version']['neighbors'])):
            metrics=score(item['sample'],pool,neighbors)
            flagged=metrics['density']<metrics['threshold']
            positive=item['verdict']==POSITIVE
            if positive and not flagged:
                stats[f'miss_{side}']+=1
            if not positive and flagged:
                stats[f'false_{side}']+=1
    return stats

def calculate(data):
    if data.get('kind')=='trial':
        return evaluate(data)
    return score(data['source'],data['pool'],data.get('neighbors',4))
