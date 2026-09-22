import sys,json,torch
from pathlib import Path
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer
root=Path('/Users/zhengbinheng/Desktop/PRM Project');sys.path.insert(0,str(root/'skywork-o1-prm-inference'))
from model_utils.prm_model import PRM_MODEL
from model_utils.io_utils import prepare_input
payload=json.loads((root/'results/formal_50_scores.json').read_text());config=payload['config']
snapshot=snapshot_download(config['model'],revision=config['model_snapshot'],local_files_only=True)
tokenizer=AutoTokenizer.from_pretrained(snapshot,local_files_only=True)
model=PRM_MODEL.from_pretrained(snapshot,device_map={'':'mps'},torch_dtype=torch.float16,low_cpu_mem_usage=True,attn_implementation='sdpa',local_files_only=True).eval();model.v_head.to(device='mps',dtype=torch.float32)
state=torch.load(Path(snapshot)/'pytorch_model.bin',map_location='cpu',mmap=True,weights_only=True)
assert torch.equal(model.v_head.summary.weight.detach().cpu(),state['v_head.summary.weight'].float())
assert torch.equal(model.v_head.summary.bias.detach().cpu(),state['v_head.summary.bias'].float())
selected={('formal_001','C-B'),('formal_018','E-N'),('formal_018','E-A'),('formal_039','E-N'),('formal_039','E-A'),('formal_050','E-A')};checked=[]
for row in payload['results']:
 if (row['formal_id'],row['condition']) not in selected:continue
 ids,steps,flags=prepare_input(row['problem'],row['response'],tokenizer,step_token='\n');x=torch.tensor([ids],device='mps')
 with torch.inference_mode():
  output=model(input_ids=x,attention_mask=torch.ones_like(x),return_probs=True,use_cache=False);score=output[2][0,-1].float().cpu().item()
 diff=abs(score-row['score']);print(row['formal_id'],row['condition'],diff,flush=True)
 checked.append({'formal_id':row['formal_id'],'condition':row['condition'],'saved':row['score'],'recomputed':score,'absolute_difference':diff})
 del output,x
 torch.mps.empty_cache()
assert len(checked)==6 and max(r['absolute_difference'] for r in checked)<=1e-6
Path('/private/tmp/prm_runtime_audit.json').write_text(json.dumps({'loaded_head_matches_checkpoint':True,'checks':checked},indent=2))
print('PASS: value head and six selected scores verified; original results unchanged.')
