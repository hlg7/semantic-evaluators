import hashlib,importlib.metadata,json,os
from pathlib import Path
from PIL import Image
from .backends import Backend,PredictionError
from .io import atomic_json,digest,load_json
from .protocol import observation_task
from .scoring import judge


def run(rows,config,output,tool='all',factory=Backend):
    """One model in memory at a time. Complete successes resume; failed attempts survive."""
    if tool not in ['all','grounding_dino','qwen_vlm']:raise ValueError('Invalid tool')
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    lock=out/'.running.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise RuntimeError('Output locked; verify no process is running before removing stale .running.lock')
    os.write(fd,str(os.getpid()).encode());os.close(fd)
    try:
        pkg=Path(__file__).parent
        sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pkg.iterdir() if p.suffix in ['.py','.json']}
        versions={}
        for name in ['torch','torchvision','transformers','Pillow','accelerate']:
            try:versions[name]=importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:versions[name]=None
        manifest={'schema_version':1,'config':config,'sources':sources,'versions':versions,'inputs':rows,'input_digest':digest(rows)}
        mp=out/'manifest.json'
        if mp.exists() and load_json(mp)!=manifest:raise ValueError('Output configuration/input mismatch; use a new output directory')
        atomic_json(mp,manifest);pred=out/'predictions';pred.mkdir(exist_ok=True)
        selected=[t for t in ['grounding_dino','qwen_vlm'] if tool in ['all',t]]
        for t in selected:
            subset=[r for r in rows if r['check']['primary_evaluator'].startswith(t)];pending=[]
            for r in subset:
                p=pred/(r['id']+'.json')
                if p.exists():
                    old=load_json(p)
                    if old.get('input_digest')!=r['input_digest']:raise ValueError('Prediction provenance mismatch')
                    if old['status']!='evaluation_error':continue
                pending.append(r)
            if not pending:continue
            backend=factory(t,config)
            try:
                for i,r in enumerate(pending,1):
                    dest=pred/(r['id']+'.json');history=[]
                    if dest.exists():
                        old=load_json(dest);history=old.pop('previous_errors',[])+[old]
                    base={'id':r['id'],'input_digest':r['input_digest'],'image_sha256':r['image_sha256'],'semantic':r['check']['semantic'],
                          'subtype':r['check']['subtype'],'tool':t,'metadata':r['metadata'],'baseline_id':r['baseline_id']}
                    try:
                        if hashlib.sha256(Path(r['image']).read_bytes()).hexdigest()!=r['image_sha256']:raise ValueError('Image changed after preflight')
                        with Image.open(r['image']) as im:im=im.convert('RGB');observation=backend.predict(im,observation_task(r['check']))
                        result={**base,**observation,**judge(observation['observation'],r['check'])}
                    except PredictionError as exc:
                        result={**base,'status':'evaluation_error','success':None,'absolute_error':None,'error':str(exc),'raw':exc.raw,'attempts':exc.attempts}
                    if history:result['previous_errors']=history
                    atomic_json(dest,result)
                    print(f'{t} {i}/{len(pending)} {r["id"]} {result["status"]}',flush=True)
            finally:backend.close()
        statuses=[]
        for r in rows:
            if tool!='all' and not r['check']['primary_evaluator'].startswith(tool):continue
            p=pred/(r['id']+'.json');statuses.append(load_json(p)['status'] if p.exists() else 'missing_output')
        return 1 if any(s in ['evaluation_error','missing_output'] for s in statuses) else 0
    finally:lock.unlink(missing_ok=True)
