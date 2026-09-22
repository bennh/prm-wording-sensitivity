"""Independently audit the frozen local PRM artifacts without model inference.

Run from the project environment: python audit_project.py
Outputs are written only to results/project_audit. Existing experimental data are read-only.
"""
import ast
import collections
import hashlib
import importlib.metadata
import json
import operator
import platform
import re
import subprocess
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent

def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def check(condition, message):
    if not condition:raise ValueError(message)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def integer_expression(expression):
    operations={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Pow:operator.pow}
    def visit(node):
        if isinstance(node,ast.Constant) and type(node.value) is int:return node.value
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.USub):return -visit(node.operand)
        if isinstance(node,ast.BinOp) and type(node.op) in operations:return operations[type(node.op)](visit(node.left),visit(node.right))
        raise ValueError('Unexpected target expression')
    return visit(ast.parse(expression,mode='eval').body)

def main():
    data=ROOT/'data';out=ROOT/'results/project_audit';out.mkdir(parents=True,exist_ok=True)
    raw=read_rows(ROOT/'test.jsonl');source=read_rows(data/'formal_50_source.jsonl');bases=read_rows(data/'formal_50.jsonl');variants=read_rows(data/'formal_50_variants.jsonl');dev=read_rows(data/'dev_5.jsonl')
    lookup={r['unique_id']:r for r in raw};dev_ids={r['problem_id'] for r in dev}
    selection=json.loads((data/'formal_50_manifest.json').read_text());construction=json.loads((data/'formal_50_construction_manifest.json').read_text())
    check(len(raw)==len(lookup)==500,'Invalid source size or duplicate IDs')
    check(digest(ROOT/'test.jsonl')==selection['source_sha256'],'Full source changed')
    check(len(source)==len(bases)==50,'Wrong formal size')
    check([r['unique_id'] for r in source]==selection['selected_ids'],'Selection order differs')
    check(digest(data/'formal_50_source.jsonl')==construction['source_sha256'],'Selected source hash differs')
    check(digest(data/'formal_50_selection.jsonl')==construction['selection_sha256'],'Selection metadata hash differs')
    check(all(lookup[r['unique_id']]==r for r in source),'Selected source differs from original')
    check(not dev_ids.intersection(r['problem_id'] for r in bases),'Development contamination')
    eligible=[r for r in raw if r['unique_id'] not in dev_ids and r['subject'] in {'Algebra','Prealgebra','Intermediate Algebra'} and r['level']<=3 and '[asy]' not in r['problem']+r['solution']]
    check(len(eligible)==selection['filter_candidate_count'],'Candidate count differs')
    templates={'B':'{step}','N':'For this step, {step}','A':'Without any doubt, {step}'}
    generated=[]
    for base,s in zip(bases,source):
        check(base['problem_id']==s['unique_id'],'ID mismatch')
        for key,original in [('problem','problem'),('source_solution','solution'),('answer','answer')]:check(base[key]==s[original],f'Source field changed: {key}')
        n=integer_expression(base['target_expression_python'])
        check(n==base['correct_result'] and n+1==base['incorrect_result'],'Invalid arithmetic label')
        c,e=base['correct_step'],base['incorrect_step']
        # Numeric tokens may occur in the expression; only the final result changes.
        numbers=list(re.finditer(r'-?\d+',c));last=numbers[-1]
        check(int(last.group())==n,'Target text does not match arithmetic metadata')
        check(c[:last.start()]+str(n+1)+c[last.end():]==e,'Error changes more than the final integer')
        for label,text in [('C',c),('E',e)]:
            for tone,template in templates.items():
                stem=text if tone=='B' else text[0].lower()+text[1:]
                steps=base['prefix_steps']+[template.format(step=stem)]
                generated.append((base['problem_id'],label+'-'+tone,base['problem'],steps))
    check(len(variants)==300,'Invalid variant count')
    for v,(pid,condition,problem,steps) in zip(variants,generated):
        check((v['problem_id'],v['condition'],v['problem'],v['steps'])==(pid,condition,problem,steps),'Variant construction differs')
        check(v['response']=='\n'.join(steps) and v['target_step_index']==len(steps)-1,'Invalid response or target index')
    scores=json.loads((ROOT/'results/formal_50_scores.json').read_text())
    check(scores['status']=='complete' and len(scores['results'])==300,'Incomplete scoring')
    cfg=scores['config']
    for name,key in [('formal_50.jsonl','data_sha256'),('formal_50_variants.jsonl','variants_sha256')]:
        check(digest(data/name)==cfg[key]==construction['artifact_sha256'][name],'Broken frozen hash chain')
    for name,key in [('run_formal_prm.py','script_sha256'),('six_variant_demo.py','summary_code_sha256')]:check(digest(ROOT/name)==cfg[key],'Scoring code changed since inference')
    upstream=ROOT/'skywork-o1-prm-inference'
    for name,h in cfg['upstream_code_sha256'].items():check(digest(upstream/name)==h,'Upstream scoring code changed')
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    sys.path.insert(0,str(upstream))
    from model_utils.io_utils import prepare_input
    tokenizer=AutoTokenizer.from_pretrained(snapshot_download(cfg['model'],revision=cfg['model_snapshot'],local_files_only=True),local_files_only=True)
    groups={};prefix_spread=0.0
    for r,v in zip(scores['results'],variants):
        check(all(r[k]==value for k,value in v.items()),'Scores attached to different inputs')
        ids,steps,flags=prepare_input(v['problem'],v['response'],tokenizer,step_token='\n')
        check(len(ids)==r['input_tokens'] and len(ids)<=512 and len(steps)==sum(flags)==len(v['steps']),'Tokenizer reconstruction mismatch')
        check(r['target_token_index']==len(ids)-1 and flags[-1]==1,'Target token mismatch')
        check(r['score']==r['step_scores'][-1],'Target score extraction mismatch')
        groups.setdefault(r['problem_id'],{})[r['condition']]=r
    conditions=['C-B','C-N','C-A','E-B','E-N','E-A']
    x=np.array([[groups[b['problem_id']][c]['score'] for c in conditions] for b in bases])
    check(np.isfinite(x).all() and ((x>=0)&(x<=1)).all(),'Invalid scores')
    for g in groups.values():prefix_spread=max(prefix_spread,float(np.ptp([g[c]['step_scores'][:-1] for c in conditions],axis=0).max()))
    check(prefix_spread==0,'Prefix scores differ')
    cb,cn,ca,eb,en,ea=x.T
    values={'wrong_confidence_effect':ea-en,'correct_confidence_effect':ca-cn,'gap_reduction':cn-en-ca+ea,'neutral_correct_wrong_gap':cn-en,'confident_correct_wrong_gap':ca-ea,'baseline_correct_wrong_gap':cb-eb,'wrong_neutral_vs_baseline':en-eb,'wrong_confident_vs_baseline':ea-eb}
    analysis=json.loads((ROOT/'results/formal_analysis/analysis_summary.json').read_text())
    rng=np.random.default_rng(analysis['seed']);idx=rng.integers(0,50,(analysis['bootstrap_replicates'],50))
    independently_recomputed={}
    for name,a in values.items():
        # Independent one-metric computation; do not import the analysis helper.
        ci=np.quantile(np.sum(a[idx],axis=1)/50,[.025,.975])
        expected=analysis['paired_statistics'][name]
        check(abs(float(a.mean())-expected['mean'])<1e-12 and np.allclose(ci,[expected['ci_low'],expected['ci_high']],rtol=0,atol=1e-12),'Analysis mismatch: '+name)
        independently_recomputed[name]={'mean':float(a.mean()),'ci_low':float(ci[0]),'ci_high':float(ci[1])}
    exploratory={}
    for name,a in [('baseline_to_neutral_gap_reduction',cb-eb-cn+en),('baseline_to_confident_gap_reduction',cb-eb-ca+ea)]:
        ci=np.quantile(a[idx].mean(1),[.025,.975]);exploratory[name]={'mean':float(a.mean()),'ci_low':float(ci[0]),'ci_high':float(ci[1])}
    repeats=collections.defaultdict(list)
    for b in bases:repeats[b['target_expression_python']].append(b['formal_id'])
    environment={name:importlib.metadata.version(name) for name in ['torch','transformers','accelerate','huggingface-hub','safetensors','numpy','matplotlib','tokenizers']}
    result={'scope':'Local artifacts; no independent upstream dataset match or training-contamination audit', 'source_rows':500,'eligible_rows':len(eligible),'formal_questions':50,'variants':300,'target_arithmetic_verified':50,'single_integer_edits_verified':50,'token_boundaries_reconstructed':300,'development_overlap':0,'prefix_score_spread':prefix_spread,'token_length_range':[min(r['input_tokens'] for r in scores['results']),max(r['input_tokens'] for r in scores['results'])], 'confident_minus_neutral_token_length_counts':dict(collections.Counter(groups[b['problem_id']]['E-A']['input_tokens']-groups[b['problem_id']]['E-N']['input_tokens'] for b in bases)), 'repeated_target_expressions':{k:v for k,v in repeats.items() if len(v)>1},'statistics':independently_recomputed,'post_hoc_baseline_checks':exploratory,'environment':environment,'python':platform.python_version(),'upstream_commit':subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip(),'raw_scores_sha256':digest(ROOT/'results/formal_50_scores.json')}
    (out/'audit_evidence.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['source_rows','eligible_rows','formal_questions','variants','target_arithmetic_verified','single_integer_edits_verified','token_boundaries_reconstructed','development_overlap']},indent=2))
    print('PASS: all local integrity and independent calculation checks.')

if __name__=='__main__':main()
