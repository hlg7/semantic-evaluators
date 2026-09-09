import hashlib,json,re
from pathlib import Path
from .protocol import build_check,validate_check


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def load_json(path):return json.loads(Path(path).read_text())
def atomic_json(path,value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def load_manifest(path,image_root=None):
    from PIL import Image
    path=Path(path);root=Path(image_root) if image_root else path.resolve().parent
    rows=[];ids=set()
    for number,line in enumerate(path.read_text().splitlines(),1):
        if not line.strip():continue
        r=json.loads(line);identifier=r.get('id')
        if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',identifier) or identifier in ids:
            raise ValueError(f'Invalid/duplicate id on line {number}')
        ids.add(identifier)
        if not isinstance(r.get('image'),str) or not r['image']:raise ValueError('Missing image path')
        p=Path(r['image']);p=p if p.is_absolute() else root/p;p=p.resolve()
        rawhash=hashlib.sha256(p.read_bytes()).hexdigest()
        if r.get('image_sha256') is not None and r['image_sha256']!=rawhash:raise ValueError(f'Image byte hash mismatch: {identifier}')
        with Image.open(p) as im:
            im.load()
            if getattr(im,'n_frames',1)!=1:raise ValueError('Animated/multipage images are unsupported')
            size=list(im.size)
        check=validate_check(r['check']) if 'check' in r else build_check(r)
        metadata=r.get('metadata',{})
        if not isinstance(metadata,dict):raise ValueError('metadata must be an object')
        row={'id':identifier,'image':str(p),'image_sha256':rawhash,'image_size':size,'check':check,'metadata':metadata,'baseline_id':r.get('baseline_id')}
        row['input_digest']=digest(row);rows.append(row)
    if not rows:raise ValueError('Empty manifest')
    byid={r['id']:r for r in rows}
    for r in rows:
        if r['baseline_id'] is not None:
            b=byid.get(r['baseline_id'])
            if b is None:raise ValueError('baseline_id must refer to a row in this manifest')
            key=lambda x:{k:x['check'][k] for k in ['semantic','subtype','evaluator_input','scoring_only']}
            if key(r)!=key(b):raise ValueError('Baseline must use identical task and reference definition')
            for field in ['backbone','prompt_id','seed']:
                if field in r['metadata'] and field in b['metadata'] and r['metadata'][field]!=b['metadata'][field]:raise ValueError('Baseline metadata mismatch: '+field)
            if b['baseline_id'] not in [None,b['id']]:raise ValueError('Baseline chains are unsupported')
    return rows


def load_config(path=None):
    c=load_json(path or Path(__file__).with_name('defaults.json'))
    for tool in ['grounding_dino','qwen_vlm']:
        for k in ['revision','processor_revision']:
            if not re.fullmatch('[0-9a-f]{40}',c[tool][k]):raise ValueError('Pin model and processor revisions to commit SHA')
    for k in ['box_threshold','text_threshold','nms_iou']:
        if not 0<=c['grounding_dino'][k]<=1:raise ValueError('Invalid detection threshold')
    for k in ['epsilon_x','epsilon_y']:
        if not 0<c['geometry'][k]<1:raise ValueError('Invalid normalized tolerance')
    limits=c['qwen_vlm']['image_pixel_limits']
    if not 0<limits['min_pixels']<=limits['max_pixels']:raise ValueError('Invalid pixel limits')
    decoding=c['qwen_vlm']['decoding']
    if decoding['do_sample'] is not False or type(decoding['max_new_tokens']) is not int or decoding['max_new_tokens']<1:raise ValueError('Use deterministic greedy decoding')
    return c
