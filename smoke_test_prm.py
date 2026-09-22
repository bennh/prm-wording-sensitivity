"""Small Skywork PRM check for Apple Silicon; not a research experiment.

Uses the model owner's inference implementation in skywork-o1-prm-inference.
Source: https://github.com/SkyworkAI/skywork-o1-prm-inference
"""

import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / "skywork-o1-prm-inference"
MODEL_ID = "Skywork/Skywork-o1-Open-PRM-Qwen-2.5-1.5B"

# Configure before importing Transformers / huggingface_hub. Use regular HTTP
# after the Xet transport failed while downloading the checkpoint.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "30")


def download_checkpoint():
    """Persist small chunks and retry interrupted HTTP streams from cache."""
    import requests
    from huggingface_hub import constants, hf_hub_download

    # hub 0.36 defaults to 10 MiB: this connection broke before one whole
    # chunk arrived. Smaller chunks preserve progress before a disconnect.
    constants.DOWNLOAD_CHUNK_SIZE = 256 * 1024
    for attempt in range(1, 6):
        print(f"Downloading/checking weights (attempt {attempt}/5; keeping the existing cache)", flush=True)
        try:
            return hf_hub_download(MODEL_ID, "pytorch_model.bin")
        except (requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as error:
            if attempt == 5:
                raise SystemExit(
                    "Repeated connection failures; retries stopped. Downloaded cache data has been preserved.\n"
                    "Switch networks or check your proxy connection, then run the script again."
                ) from error
            print(f"Connection interrupted ({type(error).__name__}); attempting to resume in 3 seconds.", flush=True)
            time.sleep(3)


def main():
    if not (UPSTREAM / "model_utils" / "prm_model.py").is_file():
        raise SystemExit(
            "The official scoring code is missing. Run this command in the project directory:\n"
            "git clone https://github.com/SkyworkAI/skywork-o1-prm-inference.git"
        )

    import torch
    from transformers import AutoTokenizer

    sys.path.insert(0, str(UPSTREAM))
    from model_utils.prm_model import PRM_MODEL
    from model_utils.io_utils import prepare_input

    if not torch.backends.mps.is_available():
        raise SystemExit("MPS is unavailable. Check that the prm-study environment is active.")

    print("[1/3] Loading the tokenizer. The first run requires an internet connection.", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    print("[2/3] Loading the model. The first run downloads several GB of weights.", flush=True)
    download_checkpoint()
    model = PRM_MODEL.from_pretrained(
        MODEL_ID,
        device_map={"": "mps"},
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
        attn_implementation="sdpa",
    ).eval()
    # The upstream value head is kept in float32 for scoring stability.
    model.v_head.to(device="mps", dtype=torch.float32)
    if not all(torch.isfinite(p).all().item() for p in model.v_head.parameters()):
        raise RuntimeError("The value head contains non-finite values.")

    print("[3/3] Scoring two short inputs separately.", flush=True)
    problem = "A shop has 12 apples and receives 3 more. It sells 2 apples. How many apples remain?"
    cases = {
        "correct": "After receiving the delivery, the shop has 12 + 3 = 15 apples.",
        "incorrect": "After receiving the delivery, the shop has 12 + 3 = 16 apples.",
    }
    results = []
    for label, step in cases.items():
        ids, steps, flags = prepare_input(problem, step, tokenizer, step_token="\n")
        if len(steps) != 1 or sum(flags) != 1:
            raise RuntimeError("Each test input must contain exactly one target step.")
        if len(ids) > 256:
            raise RuntimeError("The test input is unexpectedly long.")
        target = flags.index(1)
        input_ids = torch.tensor([ids], dtype=torch.long, device="mps")
        started = time.perf_counter()
        with torch.inference_mode():
            _, _, rewards = model(
                input_ids=input_ids,
                attention_mask=torch.ones_like(input_ids),
                return_probs=True,
                use_cache=False,
            )
            score = rewards[0, target].float().cpu().item()
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise RuntimeError(f"Invalid score:{score}")
        results.append({"label": label, "step": step, "score": score,
                        "seconds": time.perf_counter() - started})
        print(f"{label}: {score:.8f}", flush=True)
        del rewards, input_ids
        torch.mps.empty_cache()

    output = ROOT / "results" / "smoke_test.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({"model": MODEL_ID, "device": "mps",
                                 "purpose": "smoke test only",
                                 "problem": problem, "results": results},
                                ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Done. Results saved to:{output}")
    print("These results only validate the execution pipeline; they are not formal experimental conclusions.")


if __name__ == "__main__":
    main()
