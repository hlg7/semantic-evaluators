"""Generic group and optional baseline summaries; no assumptions about scales/seeds."""
from collections import Counter,defaultdict
from pathlib import Path
from .io import atomic_json,digest,load_json
from .scoring import judge


def summarize(output):
    out=Path(output);manifest=load_json(out/'manifest.json');inputs=manifest['inputs']
    if digest(inputs)!=manifest['input_digest']:raise ValueError('Corrupt manifest')
    records=[];byid={}
    paths=list((out/'predictions').glob('*.json'));expected={r['id'] for r in inputs}
    if {p.stem for p in paths}-expected:raise ValueError('Unexpected result files')
    for r in inputs:
        p=out/'predictions'/(r['id']+'.json')
        if not p.exists():q={'id':r['id'],'status':'missing_output','success':None,'absolute_error':None}
        else:
            q=load_json(p)
            if q['id']!=r['id'] or q['input_digest']!=r['input_digest']:raise ValueError('Prediction/input mismatch')
            if q['status']!='evaluation_error':
                score=judge(q['observation'],r['check'])
                if any(q[k]!=v for k,v in score.items()):raise ValueError('Saved score mismatch')
        q={**q,'semantic':r['check']['semantic'],'subtype':r['check']['subtype'],'metadata':r['metadata'],'baseline_id':r['baseline_id']}
        records.append(q);byid[q['id']]=q
    for q in records:
        b=byid.get(q['baseline_id']);q['baseline_success']=b['success'] if b else None
        q['paired_delta']=q['success']-b['success'] if b and q['success'] is not None and b['success'] is not None else None
    groups=defaultdict(list)
    for q in records:
        # Deliberately group different backbones separately. Arbitrary metadata remains in results.
        m=q['metadata'];key=(q['semantic'],q['subtype'],str(m.get('backbone','unspecified')),str(m.get('condition','unspecified')))
        groups[key].append(q)
    avg=lambda xs:sum(xs)/len(xs) if xs else None
    summaries=[]
    for key,rs in sorted(groups.items()):
        valid=[q for q in rs if q['success'] is not None];pairs=[q for q in valid if q['paired_delta'] is not None];positive=[q for q in pairs if q['baseline_success']==1]
        counts=[q['absolute_error'] for q in valid if q['absolute_error'] is not None]
        summaries.append(dict(zip(['semantic','subtype','backbone','condition'],key),n_total=len(rs),n_valid=len(valid),
          statuses=dict(Counter(q['status'] for q in rs)),success_rate=avg([q['success'] for q in valid]),
          uncertain_rate=avg([int(q['status'] in ['unclear','ambiguous']) for q in valid]),missing_object_rate=avg([int(q['status']=='missing') for q in valid]),
          paired_n=len(pairs),paired_delta=avg([q['paired_delta'] for q in pairs]),baseline_correct_n=len(positive),retention=avg([q['success'] for q in positive]),
          count_target_mae=avg(counts),count_numeric_n=len(counts)))
    result={'status':'complete' if all(q['status'] not in ['evaluation_error','missing_output'] for q in records) else 'incomplete_or_errors',
      'scientific_status':'exploratory_automatic_scores','n_total':len(records),'n_valid':sum(q['success'] is not None for q in records),'groups':summaries}
    atomic_json(out/'summary.json',result)
    (out/'results.jsonl').write_text(''.join(__import__('json').dumps(q)+'\n' for q in records))
    return result
