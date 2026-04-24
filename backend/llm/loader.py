"""
Llama-3.2-1B-Instruct loader — lazy singleton on Apple MPS.

Design decisions:
- **Lazy load on first call**, not at Django boot. Keeps the app responsive
  even when the model hasn't been downloaded yet or the machine lacks the
  expected hardware.
- **MPS on Apple Silicon, CPU fallback** everywhere else. No CUDA path
  (laptop dev target).
- **fp16 on MPS** — no bitsandbytes (not supported on MPS).
- **SDPA attention** for a free speedup on PyTorch 2.x.
- **Greedy decoding** — faster, more deterministic, and our outputs are
  structured JSON where sampling hurts.
- **Errors are surfaced, not swallowed**. If the model can't load, callers
  get a clear RuntimeError with the cause — downstream agents decide how
  to degrade.
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Optional

DEFAULT_MODEL_ID = 'meta-llama/Llama-3.2-1B-Instruct'


@dataclass
class LoadedLLM:
    model_id: str
    tokenizer: object
    model: object
    device: str
    dtype: str


_lock = threading.Lock()
_loaded: Optional[LoadedLLM] = None


def _pick_device() -> tuple[str, str]:
    import torch
    if torch.backends.mps.is_available():
        return 'mps', 'float16'
    if torch.cuda.is_available():
        return 'cuda', 'float16'
    return 'cpu', 'float32'


def _load(model_id: str) -> LoadedLLM:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device, dtype_name = _pick_device()
    torch_dtype = getattr(torch, dtype_name)

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        dtype=torch_dtype,
        attn_implementation='sdpa',
    ).to(device)
    model.eval()

    return LoadedLLM(
        model_id=model_id,
        tokenizer=tokenizer,
        model=model,
        device=device,
        dtype=dtype_name,
    )


def get_llm(model_id: str = DEFAULT_MODEL_ID) -> LoadedLLM:
    """Return the cached singleton, loading on first call. Thread-safe."""
    global _loaded
    if _loaded is not None and _loaded.model_id == model_id:
        return _loaded
    with _lock:
        if _loaded is not None and _loaded.model_id == model_id:
            return _loaded
        _loaded = _load(model_id)
        return _loaded


def is_loaded() -> bool:
    return _loaded is not None


def generate(
    prompt_messages: list[dict],
    *,
    max_new_tokens: int = 512,
    temperature: float = 0.0,
) -> str:
    """Run a chat-formatted generation. Returns the assistant's reply text.

    `prompt_messages` is OpenAI-style: [{'role':'system', 'content': '...'},
                                         {'role':'user',   'content': '...'}]
    """
    import torch

    llm = get_llm()
    tok = llm.tokenizer
    model = llm.model

    inputs = tok.apply_chat_template(
        prompt_messages,
        add_generation_prompt=True,
        return_tensors='pt',
        return_dict=True,
    ).to(llm.device)

    gen_kwargs = dict(
        max_new_tokens=max_new_tokens,
        use_cache=True,
    )
    if temperature <= 0.0:
        gen_kwargs['do_sample'] = False
    else:
        gen_kwargs.update(do_sample=True, temperature=temperature)

    prompt_len = inputs['input_ids'].shape[-1]
    with torch.no_grad():
        out = model.generate(**inputs, **gen_kwargs)

    # Strip the prompt, decode only the newly generated tokens.
    new_tokens = out[0, prompt_len:]
    return tok.decode(new_tokens, skip_special_tokens=True).strip()
