import hashlib,json,tempfile,unittest
from pathlib import Path
from PIL import Image
from semantic_evaluators.protocol import build_check,observation_task,validate_check
from semantic_evaluators.scoring import judge,parse_observation,geometry
from semantic_evaluators.io import load_manifest,load_config
from semantic_evaluators.runner import run
from semantic_evaluators.summary import summarize
from semantic_evaluators.backends import PredictionError

class ProtocolTests(unittest.TestCase):
    def task(self,**kwargs):return build_check(dict(semantic='color',objects=['bicycle'],expected='red',**kwargs))
    def test_six_tasks(self):
        for sem,sub,objs,expected in [('object','identity',['owl'],False),('count','single_category',['owl'],17),('color','color',['owl'],'red'),('shape','outline',['plate'],'oval'),('texture','pattern',['shirt'],'striped'),('texture','surface',['stone'],'rough'),('spatial_relation','left_right',['owl','tree'],'left'),('spatial_relation','above_below',['owl','tree'],'aligned'),('spatial_relation','front_behind',['owl','tree'],'behind'),('spatial_relation','containment',['owl','box'],'inside')]:
            c=build_check({'semantic':sem,'subtype':sub,'objects':objs,'expected':expected});validate_check(c)
            self.assertEqual(judge({'status':'ok','answer':expected},c)['success'],1)
    def test_answer_isolation(self):
        a=build_check({'semantic':'color','objects':['bicycle'],'expected':'red'});b=build_check({'semantic':'color','objects':['bicycle'],'expected':'blue'})
        self.assertEqual(observation_task(a),observation_task(b));self.assertNotIn('scoring_only',observation_task(a))
    def test_unseen_noun(self):self.assertIn('harpsichord',build_check({'semantic':'object','objects':['harpsichord'],'expected':True})['evaluator_input']['qwen_question'])
    def test_notebook(self):
        c=build_check({'semantic':'object','objects':['notebook'],'expected':True});self.assertEqual(c['evaluator_input']['detector_queries'],['paper notebook'])
    def test_explicit_subtype(self):
        with self.assertRaises(ValueError):build_check({'semantic':'texture','objects':['stone'],'expected':'rough'})
    def test_count_bool_invalid(self):
        with self.assertRaises(ValueError):build_check({'semantic':'count','objects':['owl'],'expected':True})
    def test_schema_and_invalid_category(self):
        c=self.task()
        for raw in ['{}','{"identity_status":"present","status":"ok","answer":"silver"}','{"identity_status":"missing","status":"ok","answer":"red"}']:
            with self.assertRaises(ValueError):parse_observation(raw,observation_task(c))
    def test_missing_is_zero(self):self.assertEqual(judge({'status':'missing','answer':None},self.task())['success'],0)
    def test_non_square_geometry(self):
        boxes=[[[0,0,20,20]],[[100,30,120,50]]]
        self.assertEqual(geometry(boxes,'x',.02,400)['answer'],'left')
        self.assertEqual(geometry(boxes,'y',.02,100)['answer'],'above')
    def test_geometry_ambiguity(self):self.assertEqual(geometry([[[0,0,1,1],[2,2,3,3]],[[8,8,9,9]]],'x',.02,10)['status'],'ambiguous')

class FakeBackend:
    calls=0;fail=False
    def __init__(self,tool,config):pass
    def close(self):pass
    def predict(self,image,task):
        FakeBackend.calls+=1
        assert 'scoring_only' not in task
        if FakeBackend.fail:raise PredictionError('bad JSON','bad',['bad','bad'])
        answer='red' if image.getpixel((0,0))[0]>0 else 'blue'
        obs={'identity_status':'present','status':'ok','answer':answer,'evidence':'test fixture'}
        return {'observation':obs,'raw':json.dumps(obs),'attempts':[json.dumps(obs)]}

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.manifest=self.root/'input.jsonl';self.out=self.root/'out'
        Image.new('RGB',(320,180),'red').save(self.root/'base.png');Image.new('RGB',(160,90),'blue').save(self.root/'edit.png')
        self.raw=[{'id':'base','image':'base.png','semantic':'color','objects':['car'],'expected':'red','metadata':{'backbone':'test','seed':1}},
          {'id':'edit','image':'edit.png','semantic':'color','objects':['car'],'expected':'red','baseline_id':'base','metadata':{'backbone':'test','seed':1}}]
        self.write();FakeBackend.calls=0;FakeBackend.fail=False
    def tearDown(self):self.tmp.cleanup()
    def write(self):self.manifest.write_text(''.join(json.dumps(r)+'\n' for r in self.raw))
    def test_run_resume_and_summary(self):
        rows=load_manifest(self.manifest);self.assertEqual(rows[0]['image_size'],[320,180]);config=load_config()
        self.assertEqual(run(rows,config,self.out,factory=FakeBackend),0);self.assertEqual(FakeBackend.calls,2)
        run(rows,config,self.out,factory=FakeBackend);self.assertEqual(FakeBackend.calls,2)
        s=summarize(self.out);self.assertEqual(s['n_valid'],2)
        rs=[json.loads(x) for x in (self.out/'results.jsonl').read_text().splitlines()];self.assertEqual(rs[1]['paired_delta'],-1)
    def test_retry_preserves_errors(self):
        rows=load_manifest(self.manifest);config=load_config();FakeBackend.fail=True
        self.assertEqual(run(rows,config,self.out,factory=FakeBackend),1);self.assertEqual(summarize(self.out)['n_valid'],0)
        FakeBackend.fail=False;run(rows,config,self.out,factory=FakeBackend)
        r=json.loads((self.out/'predictions/base.json').read_text());self.assertEqual(r['previous_errors'][0]['raw'],'bad')
    def test_changed_image_refuses_resume(self):
        config=load_config();run(load_manifest(self.manifest),config,self.out,factory=FakeBackend)
        Image.new('RGB',(320,180),'green').save(self.root/'base.png')
        with self.assertRaises(ValueError):run(load_manifest(self.manifest),config,self.out,factory=FakeBackend)
    def test_hash_check(self):
        self.raw[0]['image_sha256']='0'*64;self.write()
        with self.assertRaises(ValueError):load_manifest(self.manifest)
    def test_duplicate_id(self):
        self.raw[1]['id']='base';self.write()
        with self.assertRaises(ValueError):load_manifest(self.manifest)
    def test_baseline_mismatch(self):
        self.raw[1]['metadata']['seed']=2;self.write()
        with self.assertRaises(ValueError):load_manifest(self.manifest)
    def test_missing_baseline(self):
        self.raw[1]['baseline_id']='absent';self.write()
        with self.assertRaises(ValueError):load_manifest(self.manifest)
    def test_lock(self):
        self.out.mkdir();(self.out/'.running.lock').write_text('999')
        with self.assertRaises(RuntimeError):run(load_manifest(self.manifest),load_config(),self.out,factory=FakeBackend)
    def test_partial_summary(self):
        run(load_manifest(self.manifest),load_config(),self.out,tool='grounding_dino',factory=FakeBackend)
        self.assertEqual(summarize(self.out)['status'],'incomplete_or_errors')

if __name__=='__main__':unittest.main()
