"""Optional adapter: export frozen STAR checks without making STAR a runtime dependency."""
import hashlib,json
from pathlib import Path
from .io import atomic_json

def export_star(repo,output,image_root=None):
    repo=Path(repo);v3=repo/'data/semantic_eval_v3';checks={c['input_id']:c for c in json.loads((v3/'checks.json').read_text())['records']}
    metrics=[json.loads(x) for x in (repo/'reports/2026-09-06/metrics.jsonl').read_text().splitlines()]
    rows=[]
    for m in metrics:
        filename=m['name']+'.png'
        rows.append({'id':m['name'],'image':str(Path(image_root).resolve()/filename) if image_root else filename,'check':checks[m['input_id']],
          'baseline_id':m['baseline_name'],'metadata':{'backbone':'STAR','prompt_id':m['input_id'],'seed':m['seed'],'condition':m['name'].split('_s42_',1)[-1],
          'aliases':m['aliases'],'masked_scales':m['masked_scales'],'source_tensor_sha256':m['image_sha256']}})
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise FileExistsError(output)
    output.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    atomic_json(output.with_suffix('.provenance.json'),{'source':'hlg7/star-semantic-experiments','records':len(rows),
      'checks_sha256':hashlib.sha256((v3/'checks.json').read_bytes()).hexdigest(),
      'source_metrics_sha256':hashlib.sha256((repo/'reports/2026-09-06/metrics.jsonl').read_bytes()).hexdigest(),
      'note':'source_tensor_sha256 is historical generation tensor provenance, NOT PNG file bytes. No source images or checkpoints copied.'})
    return len(rows)
