"""Score 300 formal PRM inputs offline with validated automatic resumption."""

import argparse
import fcntl
import hashlib
import json
import math
import os
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from six_variant_demo import MODEL_ID, TEMPLATES, summarize

ROOT = Path(__file__).resolve().parent
REVISION = '98d69606595eedbdbbbf0a7d28efdcd462ba6a67'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_inputs():
    data = ROOT / 'data'
    rows = read_rows(data / 'formal_50.jsonl')
    variants = read_rows(data / 'formal_50_variants.jsonl')
    dev_ids = {r['problem_id'] for r in read_rows(data / 'dev_5.jsonl')}
    require(len(rows) == 50 and len({r['problem_id'] for r in rows}) == 50, 'Expected 50 distinct questions.')
    require(not dev_ids.intersection(r['problem_id'] for r in rows), 'Development overlap detected.')
    expected = []
    for row in rows:
        require(row['split'] == 'formal', 'Only formal data are allowed.')
        prefix = row['prefix_steps']
        require(bool(prefix), 'Missing shared prefix.')
        for label, field in [('C', 'correct_step'), ('E', 'incorrect_step')]:
            target = row[field]
            require(all(isinstance(s, str) and s.strip() and '\n' not in s and '\r' not in s for s in prefix + [target]), 'Invalid step text.')
            for tone, template in TEMPLATES.items():
                stem = target if tone == 'B' else target[0].lower() + target[1:]
                steps = prefix + [template.format(step=stem)]
                expected.append({'problem_id': row['problem_id'], 'formal_id': row['formal_id'], 'split': 'formal',
                                 'condition': f'{label}-{tone}', 'correct': label == 'C', 'tone': tone,
                                 'problem': row['problem'], 'steps': steps, 'target_step_index': len(steps)-1,
                                 'response': '\n'.join(steps)})
    require(variants == expected, 'Variant file differs from the constructed questions or fixed templates.')
    manifest = json.loads((data / 'formal_50_construction_manifest.json').read_text())
    for name in ['formal_50.jsonl', 'formal_50_variants.jsonl']:
        require(digest(data/name) == manifest['artifact_sha256'][name], f'Frozen data hash mismatch: {name}')
    return rows, variants


def atomic_write(path, payload):
    """Keep the previous valid checkpoint until the next one is fully written."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix=path.name+'.', suffix='.tmp', delete=False, encoding='utf-8') as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def validate_checkpoint(payload, config, variants, prepared):
    require(payload.get('config') == config, 'Checkpoint data, code, or environment differs. Do not mix runs; restore the original configuration or use a different --output.')
    results = payload.get('results')
    require(isinstance(results, list) and len(results) <= len(variants), 'Invalid checkpoint results.')
    for result, variant, (ids, positions) in zip(results, variants, prepared):
        require(all(result.get(k) == value for k, value in variant.items()), 'Checkpoint input or ordering mismatch.')
        scores = result.get('step_scores', [])
        require(len(scores) == len(positions) and all(type(s) in (int, float) and math.isfinite(s) and 0 <= s <= 1 for s in scores), 'Invalid saved scores.')
        require(result.get('score') == scores[-1], 'Saved target score mismatch.')
        require(result.get('input_tokens') == len(ids) and result.get('target_token_index') == positions[-1], 'Saved token positions mismatch.')
    return len(results)


def finalize(payload, rows):
    results = payload['results']
    require(len(results) == 300, 'Cannot finalize an incomplete run.')
    summaries = []
    for row in rows:
        group = [r for r in results if r['problem_id'] == row['problem_id']]
        require(Counter(r['condition'] for r in group) == Counter(['C-B','C-N','C-A','E-B','E-N','E-A']), 'Missing or duplicate condition.')
        summaries.append({'problem_id': row['problem_id'], 'formal_id': row['formal_id'], **summarize(group)})
    payload['per_question_summary'] = summaries
    metrics = [k for k in summaries[0] if k not in ('problem_id', 'formal_id')]
    payload['descriptive_means'] = {k: sum(r[k] for r in summaries)/50 for k in metrics}
    payload['status'] = 'complete'
    payload['completed_at'] = datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--preview', action='store_true', help='Validate data only; no tokenizer or model')
    mode.add_argument('--check-inputs', action='store_true', help='Check cached tokenizer only; no model scoring')
    parser.add_argument('--output', type=Path, default=ROOT/'results/formal_50_scores.json', help='Checkpoint path; automatically resume if it exists')
    args = parser.parse_args()
    rows, variants = load_inputs()
    print('Validated 50 questions and 300 paired inputs.', flush=True)
    if args.preview:
        print('Frozen data hashes, templates, and development isolation passed.')
        return

    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    upstream = ROOT / 'skywork-o1-prm-inference'
    sys.path.insert(0, str(upstream))
    from model_utils.io_utils import prepare_input
    model_path = snapshot_download(MODEL_ID, revision=REVISION, local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    prepared = []
    for variant in variants:
        # Reference solutions and answers are never passed to the tokenizer.
        ids, steps, flags = prepare_input(variant['problem'], variant['response'], tokenizer, step_token='\n')
        positions = [i for i, flag in enumerate(flags) if flag]
        require(len(steps) == len(positions) == len(variant['steps']), 'Unexpected step boundaries.')
        require(len(ids) <= 512 and positions[-1] == len(ids)-1, 'Invalid length or target boundary; no truncation is permitted.')
        prepared.append((ids, positions))
    print(f'All 300 token checks passed; maximum length: {max(len(ids) for ids, _ in prepared)}.', flush=True)
    if args.check_inputs:
        return

    require(torch.backends.mps.is_available(), 'MPS is unavailable. Activate the prm-study environment.')
    config = {'model': MODEL_ID, 'model_snapshot': REVISION, 'device': 'mps', 'backbone_dtype': 'float16',
              'head_dtype': 'float32', 'attention': 'sdpa', 'use_cache': False, 'max_tokens': 512,
              'torch_version': torch.__version__, 'transformers_version': transformers.__version__,
              'templates': TEMPLATES, 'data_sha256': digest(ROOT/'data/formal_50.jsonl'),
              'variants_sha256': digest(ROOT/'data/formal_50_variants.jsonl'),
              'script_sha256': digest(Path(__file__)), 'summary_code_sha256': digest(ROOT/'six_variant_demo.py'),
              'upstream_code_sha256': {str(p.relative_to(upstream)): digest(p) for p in sorted((upstream/'model_utils').rglob('*.py'))}}
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # The OS releases the advisory lock even after an interruption or crash.
    with output.with_suffix(output.suffix+'.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Another process is using this output. Stop it before resuming.')
        if output.exists():
            payload = json.loads(output.read_text())
            start = validate_checkpoint(payload, config, variants, prepared)
        else:
            payload = {'purpose': 'Formal evaluation; question-level paired analysis', 'status': 'incomplete',
                       'created_at': datetime.now(timezone.utc).isoformat(), 'config': config,
                       'expected_questions': 50, 'expected_inputs': 300, 'results': [], 'per_question_summary': []}
            start = 0
            atomic_write(output, payload)
        if start == 300:
            finalize(payload, rows)
            atomic_write(output, payload)
            print(f'All 300 scores already exist. No rescoring. Results: {output}')
            return
        print(f'Resuming from {start}/300 saved inputs. Loading the cached model once.', flush=True)
        from model_utils.prm_model import PRM_MODEL
        model = PRM_MODEL.from_pretrained(model_path, device_map={'': 'mps'}, torch_dtype=torch.float16,
                                        low_cpu_mem_usage=True, attn_implementation='sdpa', local_files_only=True).eval()
        model.v_head.to(device='mps', dtype=torch.float32)
        try:
            for i in range(start, len(variants)):
                variant = variants[i]
                ids, positions = prepared[i]
                began = time.perf_counter()
                input_ids = torch.tensor([ids], dtype=torch.long, device='mps')
                with torch.inference_mode():
                    outputs = model(input_ids=input_ids, attention_mask=torch.ones_like(input_ids), return_probs=True, use_cache=False)
                    scores = outputs[2][0, positions].float().cpu().tolist()
                require(len(scores) == len(positions) and all(math.isfinite(s) and 0 <= s <= 1 for s in scores), 'Invalid model score.')
                payload['results'].append({**variant, 'input_tokens': len(ids), 'target_token_index': positions[-1],
                                           'step_scores': scores, 'score': scores[-1], 'seconds': time.perf_counter()-began})
                atomic_write(output, payload)
                print(f"[{i+1}/300] {variant['formal_id']} {variant['condition']}: {scores[-1]:.8f}", flush=True)
                del input_ids, outputs
                torch.mps.empty_cache()
        except KeyboardInterrupt:
            print(f'\nStopped. Rerun the same command to resume from the last saved input: {output}')
            return
        finalize(payload, rows)
        atomic_write(output, payload)
        print(f'Complete: 300 scores and 50 paired summaries saved to {output}')
        print('Descriptive means are not statistical significance tests. Analyze the 50 question-level pairs.')


if __name__ == '__main__':
    main()
