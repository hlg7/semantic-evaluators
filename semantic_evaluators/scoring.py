"""Pure scoring rules. No model imports."""
import json
import re


def judge(answer, check):
    status = answer.get('status')
    if status not in ['ok','missing','ambiguous','unclear']: raise ValueError('Invalid status')
    value = answer.get('answer')
    if status != 'ok':
        if value is not None: raise ValueError('Non-ok answer must be null')
        return {'status':status, 'success':0, 'absolute_error':None}
    allowed = check['evaluator_input']['allowed_answers']
    if allowed == 'nonnegative_integer':
        if type(value) is not int or value < 0: raise ValueError('Invalid count')
    elif not any(type(value) is type(x) and value == x for x in allowed):
        raise ValueError('Invalid answer category')
    expected = check['scoring_only']['expected_answer']
    success = int(type(value) is type(expected) and value == expected)
    return {'status':'correct' if success else 'incorrect','success':success,
            'absolute_error':abs(value-expected) if check['semantic']=='count' else None}


def parse_observation(raw, check):
    # Strict JSON: invalid output is an evaluation error, never a semantic zero.
    result = json.loads(raw)
    if not isinstance(result, dict): raise ValueError('Expected object')
    if check['evaluator_input']['allowed_answers']=='nonnegative_integer' and isinstance(result.get('answer'),str) and re.fullmatch(r'[0-9]+',result['answer']):
        result['answer']=int(result['answer'])
    if check.get('require_identity_status'):
        identity=result.get('identity_status')
        if check['semantic'] in ['object','count']:
            if identity not in ['present','absent','unclear']: raise ValueError('Invalid identity status')
            if identity=='unclear' and result.get('status')!='unclear': raise ValueError('Uncertain identity cannot yield definite answer')
            if identity in ['present','absent']:
                if result.get('status')!='ok': raise ValueError('Presence/count identity conflicts with response status')
                value=result.get('answer')
                if identity=='absent' and value != (False if check['semantic']=='object' else 0): raise ValueError('Absent identity conflicts with answer')
                if identity=='present' and (value is False or value == 0): raise ValueError('Present identity conflicts with answer')
        else:
            if identity not in ['present','missing','ambiguous','unclear']: raise ValueError('Invalid identity status')
            if identity!='present' and (result.get('status')!=identity or result.get('answer') is not None):
                raise ValueError('Cannot score attribute/relation without identified target')
    dummy = dict(check, scoring_only={"expected_answer": None})
    judge(result, dummy)  # Type/category/status validation only; no target is available.
    return result


def parse_qwen(raw, check):
    return judge(parse_observation(raw, check), check)


def geometry(boxes, axis, epsilon, size):
    if any(len(b) == 0 for b in boxes): return {'status':'missing','answer':None}
    if any(len(b) != 1 for b in boxes): return {'status':'ambiguous','answer':None}
    a,b = boxes[0][0], boxes[1][0]
    i = 0 if axis == 'x' else 1
    delta = ((a[i]+a[i+2])-(b[i]+b[i+2])) / (2*size)
    if abs(delta) <= epsilon: value = 'aligned'
    else: value = ('left' if delta < 0 else 'right') if axis == 'x' else ('above' if delta < 0 else 'below')
    return {'status':'ok','answer':value}
