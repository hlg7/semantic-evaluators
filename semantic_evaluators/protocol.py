"""Backbone-independent task specifications. Expected answers stay in scoring_only."""
import json
from pathlib import Path
from .scoring import judge

RULES=json.loads(Path(__file__).with_name('rules.json').read_text())
SUBTYPES={'object':['identity'],'color':['color'],'shape':['outline'],
          'texture':['pattern','surface'],'count':['single_category'],
          'spatial_relation':['left_right','above_below','front_behind','containment']}


def build_check(row):
    sem=row.get('semantic')
    if sem not in SUBTYPES:raise ValueError('Unknown semantic')
    subtype=row.get('subtype')
    if subtype is None:
        if len(SUBTYPES[sem])!=1:raise ValueError('Specify subtype for texture/spatial_relation')
        subtype=SUBTYPES[sem][0]
    if subtype not in SUBTYPES[sem]:raise ValueError('Invalid subtype')
    objects=row.get('objects')
    required=2 if sem=='spatial_relation' else 1
    if not isinstance(objects,list) or len(objects)!=required or any(not isinstance(x,str) or not x.strip() for x in objects):
        raise ValueError('objects must contain one canonical singular noun (two for relations)')
    if objects!=[x.strip() for x in objects]:raise ValueError('Remove surrounding whitespace from nouns')
    if 'expected' not in row:raise ValueError('Missing expected answer')
    obj=objects[0];primary='qwen_vlm'
    if sem=='object':
        primary='grounding_dino';allowed=[True,False];question=f'Is any {obj} visibly present?'
    elif sem=='count':
        primary='grounding_dino';allowed='nonnegative_integer'
        question=f'How many distinct physical instances of {obj} are visible? Count across the whole image, not reflections or pictures.'
    elif sem=='color':
        allowed=RULES['COLORS']+['other','multicolored'];question=f'What is the main surface color of the {obj}? Ignore small decorations, highlights and shadows.'
    elif sem=='shape':
        allowed=RULES['SHAPES']+['other']
        question=f'After confirming the identity of the {obj}, what is its overall boundary shape, excluding patterns, holes, parts and shadows? Use the object shape when perspective is identifiable; otherwise use unclear. Round means circular rather than merely curved; oval means elongated rounded outline; square and non-square rectangular are separate. Do not substitute a face of a different 3D object.'
    elif sem=='texture':
        if subtype=='surface':
            allowed=['rough','smooth','mixed','other'];question=f'Does the visible surface of the {obj} look rough, smooth, mixed, or other? Use visible surface detail, not material stereotypes.'
        else:
            allowed=['striped','checkered','polka-dotted','plain','mixed','other'];question=f'What is the dominant visible surface pattern on the {obj}, not the background?'
    else:
        a,b=objects
        if subtype=='left_right':
            primary='grounding_dino_geometry';allowed=['left','right','aligned'];question=f'From the viewer perspective, is the {a} left of, right of, or horizontally aligned with the {b}?'
        elif subtype=='above_below':
            primary='grounding_dino_geometry';allowed=['above','below','aligned'];question=f'Is the {a} above, below, or vertically aligned with the {b} in the image?'
        elif subtype=='front_behind':
            allowed=['front','behind','same_depth'];question=f'Is the {a} in front of, behind, or at the same depth as the {b}? Use depth and occlusion evidence, not vertical image position alone.'
        else:
            allowed=['inside','outside','partial'];question=f'Is the {a} inside, outside, or partially inserted into the interior space of the {b}? Inside means seated or contained in the interior; extension above an opening does not by itself make it partial. Outside means not occupying the interior. Partial means crossing the opening without clear settled containment. Use unclear when the physical relation cannot be established. Bounding-box overlap alone is not containment.'
    if sem in ['object','count']:
        schema=('For this task, identity_status must be present, absent, or unclear; never missing or ambiguous. '
                'If the object is absent, use identity_status=absent, status=ok, answer='+('false' if sem=='object' else '0')+'. '
                'If presence or exact enumeration cannot be resolved, use identity_status=unclear, status=unclear, answer=null. '
                'Otherwise use identity_status=present, status=ok and an allowed answer. Multiple instances do not make this task ambiguous.')
    else:
        schema=('For this task, identity_status must be present, missing, ambiguous, or unclear. '
                'For a non-present identity use the same status and answer=null. '
                'With present identity, an unresolved property may use status=unclear, answer=null; otherwise use status=ok and an allowed answer.')
    system=RULES['SYSTEM'];definitions=[RULES['DEFINITIONS'][n] for n in objects if n in RULES['DEFINITIONS']]
    if definitions:system+=' Category definitions for this task: '+' '.join(definitions)
    if sem=='color':system+=' '+RULES['COLOR']
    if sem=='texture' and subtype=='surface':system+=' '+RULES['SURFACE']
    check={'semantic':sem,'subtype':subtype,'primary_evaluator':primary,'protocol_version':'six_semantics_v1',
      'require_identity_status':True,'evaluator_input':{'qwen_system':system,'qwen_question':question+' Response schema for this task: '+schema,
      'response_schema':schema,'allowed_answers':allowed,'category_definitions':definitions,
      'detector_queries':['paper notebook' if n=='notebook' else n for n in objects],
      'detector_label_aliases':[['paper notebook','notebook'] if n=='notebook' else [n] for n in objects]},
      'scoring_only':{'expected_answer':row['expected']}}
    judge({'status':'ok','answer':row['expected']},check)
    return check


def validate_check(check):
    """Validate compiled imports without regenerating their frozen question strings."""
    if check['semantic'] not in SUBTYPES or check['subtype'] not in SUBTYPES[check['semantic']]:raise ValueError('Invalid compiled task')
    e=check['evaluator_input'];sem=check['semantic'];sub=check['subtype']
    primary='grounding_dino' if sem in ['object','count'] else ('grounding_dino_geometry' if sem=='spatial_relation' and sub in ['left_right','above_below'] else 'qwen_vlm')
    if check['primary_evaluator']!=primary:raise ValueError('Compiled primary-tool mismatch')
    n=2 if sem=='spatial_relation' else 1
    if len(e['detector_queries'])!=n or any(not isinstance(q,str) or not q.strip() for q in e['detector_queries']):raise ValueError('Invalid queries')
    if not isinstance(e['qwen_system'],str) or not isinstance(e['qwen_question'],str):raise ValueError('Invalid question')
    if not check.get('require_identity_status'):raise ValueError('Identity status required')
    expected=check['scoring_only']['expected_answer']
    canonical=build_check({'semantic':sem,'subtype':sub,'objects':e['detector_queries'],'expected':expected})
    if e['allowed_answers']!=canonical['evaluator_input']['allowed_answers']:raise ValueError('Unsupported answer vocabulary')
    aliases=e.get('detector_label_aliases',[[q] for q in e['detector_queries']])
    if len(aliases)!=n or any(not isinstance(a,list) or not a or any(not isinstance(v,str) or not v for v in a) for a in aliases):raise ValueError('Invalid label aliases')
    judge({'status':'ok','answer':expected},check)
    return check


def observation_task(check):
    """The backend never receives scoring_only, image IDs, baselines or metadata."""
    return {k:check[k] for k in ['semantic','subtype','require_identity_status','evaluator_input']}
