"""Lazy CUDA adapters. These receive observation tasks only, never expected answers."""
import re
from .scoring import parse_observation,geometry

class PredictionError(Exception):
    def __init__(self,message,raw=None,attempts=None):
        super().__init__(message);self.raw=raw;self.attempts=attempts or []

class Backend:
    def __init__(self,tool,config):
        import torch
        from transformers import AutoProcessor,AutoModelForZeroShotObjectDetection,Qwen3VLForConditionalGeneration
        if not torch.cuda.is_available():raise RuntimeError('Model inference requires CUDA; use validate/test locally')
        self.torch=torch;self.tool=tool;self.config=config;c=config[tool]
        torch.manual_seed(42);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.benchmark=False
        kw={'revision':c['processor_revision']}
        if tool=='qwen_vlm':kw.update(c['image_pixel_limits'])
        self.processor=AutoProcessor.from_pretrained(c['checkpoint'],**kw)
        if tool=='grounding_dino':
            self.model=AutoModelForZeroShotObjectDetection.from_pretrained(c['checkpoint'],revision=c['revision']).to('cuda').eval()
        else:
            self.model=Qwen3VLForConditionalGeneration.from_pretrained(c['checkpoint'],revision=c['revision'],torch_dtype=torch.bfloat16,attn_implementation='sdpa').to('cuda').eval()

    def close(self):
        del self.model;self.torch.cuda.empty_cache()

    def predict(self,image,task):
        e=task['evaluator_input'];raw=None;attempts=[];c=self.config[self.tool]
        try:
            with self.torch.inference_mode():
                if self.tool=='qwen_vlm':
                    messages=[{'role':'system','content':[{'type':'text','text':e['qwen_system']}]},{'role':'user','content':[
                        {'type':'image','image':image},{'type':'text','text':e['qwen_question']+' Allowed answers: '+__import__('json').dumps(e['allowed_answers'])}]}]
                    for attempt in range(2):
                        inputs=self.processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,return_dict=True,return_tensors='pt').to('cuda')
                        output=self.model.generate(**inputs,**c['decoding'])
                        raw=self.processor.decode(output[0,inputs['input_ids'].shape[1]:],skip_special_tokens=True);attempts.append(raw)
                        try:obs=parse_observation(raw,task);break
                        except (ValueError,TypeError):
                            if attempt==1:raise
                            messages[1]['content'][1]['text']+=' Schema reminder: output a JSON object with identity_status, status, answer and evidence. An ok answer must be a non-null allowed value. For missing, ambiguous or unclear use answer=null. Counts are nonnegative integers. If you cannot identify the requested objects, do not assign their attributes. Do not guess. '+e.get('response_schema','')
                else:
                    from torchvision.ops import nms
                    raw=[];retained=[]
                    for i,query in enumerate(e['detector_queries']):
                        inputs=self.processor(images=image,text=query.lower()+'.',return_tensors='pt').to('cuda');output=self.model(**inputs)
                        detected=self.processor.post_process_grounded_object_detection(output,inputs.input_ids,threshold=c['box_threshold'],text_threshold=c['text_threshold'],target_sizes=[(image.height,image.width)])[0]
                        normalize=lambda s:' '.join(re.findall(r'\w+',s.lower()))
                        aliases=e.get('detector_label_aliases',[[q] for q in e['detector_queries']])[i]
                        valid=[j for j,label in enumerate(detected['text_labels']) if normalize(label) in {normalize(v) for v in aliases}]
                        boxes=detected['boxes'][valid];scores=detected['scores'][valid]
                        boxes=boxes[nms(boxes,scores,c['nms_iou'])].cpu().tolist();retained.append(boxes)
                        raw.append({'query':query,'all_boxes':detected['boxes'].cpu().tolist(),'all_scores':detected['scores'].cpu().tolist(),'text_labels':detected['text_labels'],'retained_boxes':boxes})
                    if task['semantic']=='object':obs={'status':'ok','answer':bool(retained[0])}
                    elif task['semantic']=='count':obs={'status':'ok','answer':len(retained[0])}
                    else:
                        axis='x' if task['subtype']=='left_right' else 'y'
                        obs=geometry(retained,axis,self.config['geometry']['epsilon_'+axis],image.width if axis=='x' else image.height)
                return {'observation':obs,'raw':raw,'attempts':attempts}
        except self.torch.cuda.OutOfMemoryError:raise
        except Exception as exc:raise PredictionError(str(exc),raw,attempts) from exc
