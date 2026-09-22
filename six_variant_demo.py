"""Offline six-condition pipeline check. The apple example is not MATH-500 data."""

import argparse
import json
import math
import os
import sys
from pathlib import Path

# Read only the model already downloaded by smoke_test_prm.py.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

ROOT = Path(__file__).resolve().parent
MODEL_ID = "Skywork/Skywork-o1-Open-PRM-Qwen-2.5-1.5B"
PROBLEM = "A shop has 12 apples and receives 3 more. It sells 2 apples. How many apples remain?"
TEMPLATES = {"B": "{step}", "N": "For this step, {step}", "A": "Without any doubt, {step}"}


def build_cases():
    cases = []
    for correctness, result in [("C", 15), ("E", 16)]:
        stem = f"after receiving the delivery, the shop has 12 + 3 = {result} apples."
        for tone, template in TEMPLATES.items():
            step = stem[0].upper() + stem[1:] if tone == "B" else stem
            cases.append({"condition": f"{correctness}-{tone}",
                          "correct": correctness == "C", "tone": tone,
                          "step": template.format(step=step)})
    return cases


def summarize(rows):
    scores = {row["condition"]: row["score"] for row in rows}
    wrong_effect = scores["E-A"] - scores["E-N"]
    correct_effect = scores["C-A"] - scores["C-N"]
    neutral_gap = scores["C-N"] - scores["E-N"]
    confident_gap = scores["C-A"] - scores["E-A"]
    return {"wrong_confidence_effect": wrong_effect,
            "correct_confidence_effect": correct_effect,
            "neutral_correct_wrong_gap": neutral_gap,
            "confident_correct_wrong_gap": confident_gap,
            "gap_reduction": neutral_gap - confident_gap}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Preview all six inputs without loading the model")
    args = parser.parse_args()
    cases = build_cases()
    print("Problem:", PROBLEM)
    for case in cases:
        print(f"{case['condition']}: {case['step']}")
    if args.preview:
        return

    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer

    upstream = ROOT / "skywork-o1-prm-inference"
    if not (upstream / "model_utils" / "prm_model.py").is_file():
        raise SystemExit("The previously downloaded skywork-o1-prm-inference directory is missing.")
    sys.path.insert(0, str(upstream))
    from model_utils.prm_model import PRM_MODEL
    from model_utils.io_utils import prepare_input

    if not torch.backends.mps.is_available():
        raise SystemExit("MPS is unavailable. Use the prm-study environment that passed the smoke test.")
    model_path = snapshot_download(MODEL_ID, local_files_only=True)
    if not (Path(model_path) / "pytorch_model.bin").is_file():
        raise SystemExit("Complete model weights are missing from the local cache. Use the same environment as the successful smoke test.")
    print("\nLoading the model from the existing local cache without downloading.", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = PRM_MODEL.from_pretrained(
        model_path, device_map={"": "mps"}, torch_dtype=torch.float16,
        low_cpu_mem_usage=True, attn_implementation="sdpa", local_files_only=True,
    ).eval()
    model.v_head.to(device="mps", dtype=torch.float32)

    for case in cases:
        ids, steps, flags = prepare_input(PROBLEM, case["step"], tokenizer, step_token="\n")
        if len(steps) != 1 or sum(flags) != 1 or len(ids) > 256:
            raise RuntimeError("Unexpected target-step boundary or input length.")
        input_ids = torch.tensor([ids], dtype=torch.long, device="mps")
        with torch.inference_mode():
            outputs = model(input_ids=input_ids, attention_mask=torch.ones_like(input_ids),
                            return_probs=True, use_cache=False)
            score = outputs[2][0, flags.index(1)].float().cpu().item()
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise RuntimeError(f"Invalid score:{score}")
        case.update(score=score, input_tokens=len(ids), target_token_index=flags.index(1))
        print(f"{case['condition']}: {score:.8f}", flush=True)
        del outputs, input_ids
        torch.mps.empty_cache()

    summary = summarize(cases)
    payload = {"purpose": "six-variant pipeline demo only; not formal evaluation",
               "source": "handwritten apple example, not MATH-500",
               "model": MODEL_ID, "model_snapshot": Path(model_path).name,
               "device": "mps", "backbone_dtype": "float16", "head_dtype": "float32",
               "torch_version": torch.__version__, "transformers_version": transformers.__version__,
               "problem": PROBLEM, "templates": TEMPLATES,
               "results": cases, "summary": summary}
    output = ROOT / "results" / "six_variant_demo.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nConfidence wording effect on the incorrect step:", summary["wrong_confidence_effect"])
    print("Reduction in the correct-minus-incorrect score gap:", summary["gap_reduction"])
    print(f"Results saved to:{output}")
    print("This single-question debugging result cannot establish statistical significance and is excluded from the development and formal evaluation sets.")


if __name__ == "__main__":
    main()
