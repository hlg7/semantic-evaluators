import argparse,json
from .io import load_manifest,load_config

def main():
    p=argparse.ArgumentParser(prog='semantic-evaluators');sub=p.add_subparsers(dest='command',required=True)
    for name in ['validate','run']:
        q=sub.add_parser(name);q.add_argument('--manifest',required=True);q.add_argument('--image-root');q.add_argument('--config')
        if name=='run':q.add_argument('--output',required=True);q.add_argument('--tool',choices=['all','grounding_dino','qwen_vlm'],default='all')
    q=sub.add_parser('summarize');q.add_argument('--output',required=True)
    a=p.parse_args()
    if a.command=='summarize':
        from .summary import summarize
        result=summarize(a.output);print(json.dumps(result,indent=2));return 0 if result['status']=='complete' else 1
    rows=load_manifest(a.manifest,a.image_root);config=load_config(a.config)
    if a.command=='validate':print(f'Validated {len(rows)} records and image hashes; no models loaded.');return 0
    from .runner import run
    return run(rows,config,a.output,a.tool)

if __name__=='__main__':raise SystemExit(main())
