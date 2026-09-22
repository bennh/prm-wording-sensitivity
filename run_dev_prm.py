"""Score the five reviewed development questions offline, one input at a time."""

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from six_variant_demo import MODEL_ID, TEMPLATES, summarize

ROOT = Path(__file__).resolve().parent
REVISION = "98d69606595eedbdbbbf0a7d28efdcd462ba6a67"


def build_variants(rows):
    if len(rows) != 5 or len({r['problem_id'] for r in rows}) != 5:
        raise ValueError("Expected five distinct development questions.")
    variants = []
    for row in rows:
        if row['split'] != 'dev' or row['review_status'] != 'user_reviewed':
            raise ValueError("All questions must be reviewed development data.")
        prefix = row['prefix_steps']
        if not prefix or any(not s.strip() or '\n' in s or '\r' in s for s in prefix):
            raise ValueError("Each prefix step must be a nonempty single-line string.")
        for label, field in [('C', 'correct_step'), ('E', 'incorrect_step')]:
            original = row[field]
            if not original.strip() or '\n' in original or '\r' in original:
                raise ValueError("Each target must be a nonempty single-line string.")
            for tone, template in TEMPLATES.items():
                stem = original if tone == 'B' else original[0].lower() + original[1:]
                steps = prefix + [template.format(step=stem)]
                variants.append({'problem_id': row['problem_id'], 'condition': f'{label}-{tone}',
                                 'problem': row['problem'], 'steps': steps,
                                 'target_step_index': len(steps) - 1})
    return variants


def write_result(path, payload):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true', help='Validate and display inputs without loading a model')
    parser.add_argument('--check-inputs', action='store_true', help='Also check cached-tokenizer step boundaries without loading model weights')
    args = parser.parse_args()
    data_path = ROOT / 'data' / 'dev_5.jsonl'
    raw = data_path.read_bytes()
    rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    variants = build_variants(rows)
    print(f'Validated {len(rows)} questions and {len(variants)} inputs.')
    if args.preview:
        for v in variants:
            print(f"{v['problem_id']} | {v['condition']} | target step {v['target_step_index'] + 1}")
            print(v['steps'][-1])
        return

    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    sys.path.insert(0, str(ROOT / 'skywork-o1-prm-inference'))
    from model_utils.io_utils import prepare_input
    model_path = snapshot_download(MODEL_ID, revision=REVISION, local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    prepared = []
    for v in variants:
        ids, steps, flags = prepare_input(v['problem'], '\n'.join(v['steps']), tokenizer, step_token='\n')
        positions = [i for i, flag in enumerate(flags) if flag]
        if len(steps) != len(v['steps']) or len(positions) != len(v['steps']):
            raise ValueError('Unexpected step boundaries.')
        if len(ids) > 512:
            raise ValueError('Input exceeds the 512-token development limit; no truncation applied.')
        if positions[-1] != len(ids) - 1:
            raise ValueError('The final step boundary must be the target position.')
        prepared.append((ids, positions))
    print('All 30 inputs passed token-length and multi-step boundary checks.')
    if args.check_inputs:
        print(f'Maximum input length: {max(len(ids) for ids, _ in prepared)} tokens.')
        return

    if not torch.backends.mps.is_available():
        raise SystemExit('MPS is unavailable. Activate the prm-study environment.')
    from model_utils.prm_model import PRM_MODEL
    print('Loading the cached model once; no downloads.', flush=True)
    model = PRM_MODEL.from_pretrained(model_path, device_map={'': 'mps'},
                                    torch_dtype=torch.float16, low_cpu_mem_usage=True,
                                    attn_implementation='sdpa', local_files_only=True).eval()
    model.v_head.to(device='mps', dtype=torch.float32)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'results' / f'dev_5_scores_{stamp}.json'
    output.parent.mkdir(exist_ok=True)
    payload = {'purpose': 'development only; not formal evaluation', 'status': 'incomplete',
               'model': MODEL_ID, 'model_snapshot': REVISION, 'device': 'mps',
               'backbone_dtype': 'float16', 'head_dtype': 'float32',
               'torch_version': torch.__version__, 'transformers_version': transformers.__version__,
               'data_sha256': hashlib.sha256(raw).hexdigest(), 'templates': TEMPLATES,
               'expected_inputs': 30, 'results': [], 'per_question_summary': []}
    write_result(output, payload)
    for index, (v, (ids, positions)) in enumerate(zip(variants, prepared), 1):
        input_ids = torch.tensor([ids], dtype=torch.long, device='mps')
        with torch.inference_mode():
            outputs = model(input_ids=input_ids, attention_mask=torch.ones_like(input_ids),
                            return_probs=True, use_cache=False)
            step_scores = outputs[2][0, positions].float().cpu().tolist()
        if not all(math.isfinite(s) and 0 <= s <= 1 for s in step_scores):
            raise ValueError('Invalid step score.')
        payload['results'].append({**v, 'input_tokens': len(ids), 'target_token_index': positions[-1],
                                   'step_scores': step_scores, 'score': step_scores[-1]})
        write_result(output, payload)
        print(f"[{index}/30] {v['problem_id']} {v['condition']}: {step_scores[-1]:.8f}", flush=True)
        del input_ids, outputs
        torch.mps.empty_cache()
    for row in rows:
        group = [r for r in payload['results'] if r['problem_id'] == row['problem_id']]
        payload['per_question_summary'].append({'problem_id': row['problem_id'], **summarize(group)})
    payload['status'] = 'complete'
    write_result(output, payload)
    print(f'Results saved to: {output}')
    print('Five development questions are not sufficient for formal statistical conclusions.')


if __name__ == '__main__':
    main()
