# workerllm-runtime — call-shape recipes

Concrete OpenAI-SDK snippets for the common patterns. Drop into produced-app code.

## Pattern 1: One-shot judgment (rule verification)

```python
import os, json
from openai import OpenAI

client = OpenAI(
    api_key="not-used",
    base_url=os.environ.get("JOHN_LLM_CLIENT_URL", "http://localhost:8500") + "/v1",
)

def check_rule(rule_description: str, document_excerpt: str) -> dict:
    """Return {'verdict': 'pass'|'fail'|'needs_review', 'confidence': 0-1, 'reason': str}."""
    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": "You verify documents against a single rule. Respond with JSON only."},
            {"role": "user", "content": f"Rule: {rule_description}\n\nDocument excerpt:\n{document_excerpt}\n\nReturn JSON: {{\"verdict\": \"pass\"|\"fail\"|\"needs_review\", \"confidence\": 0.0-1.0, \"reason\": \"...\"}}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return json.loads(resp.choices[0].message.content)
```

## Pattern 2: Bulk classification

```python
def classify_batch(items: list[str], categories: list[str]) -> list[str]:
    """Classify each item into one of categories. Returns parallel list."""
    out = []
    for item in items:
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": f"Classify into one of: {', '.join(categories)}. Reply with just the category name."},
                {"role": "user", "content": item},
            ],
            temperature=0.0,
            max_tokens=20,
        )
        out.append(resp.choices[0].message.content.strip())
    return out
```

For larger batches, parallelize with `concurrent.futures.ThreadPoolExecutor` (the SDK is thread-safe).

## Pattern 3: Long-context synthesis

```python
def summarize_long_doc(doc_text: str) -> str:
    """Single-pass summary of a long document. Use Qwen3.5 for the larger context window."""
    resp = client.chat.completions.create(
        model="Qwen/Qwen3.5-397B-A17B",
        messages=[
            {"role": "system", "content": "Summarize the following document in 5-10 sentences."},
            {"role": "user", "content": doc_text},
        ],
        temperature=0.3,
        max_tokens=2000,
    )
    return resp.choices[0].message.content
```

## Pattern 4: Vision / OCR

```python
import base64

def extract_text_from_image(image_path: str) -> str:
    """OCR + layout extraction via PaddleOCR-VL."""
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    resp = client.chat.completions.create(
        model="PaddlePaddle/PaddleOCR-VL-1.5",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all text from this image. Preserve layout."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            }
        ],
        temperature=0.0,
    )
    return resp.choices[0].message.content
```

(For pure PDF parsing, prefer the ppx client — it handles layout + OCR + tables in one pass. PaddleOCR-VL via the LLM client is for ad-hoc image questions.)

## Pattern 5: Retry on transient errors

```python
import time
from openai import APIConnectionError, APITimeoutError

def call_with_retry(messages, model="deepseek-v4-flash", max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(model=model, messages=messages, temperature=0.1)
        except (APIConnectionError, APITimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
    raise RuntimeError("unreachable")
```

For more sophisticated retry (jitter, circuit breaker), bring `tenacity` as a dep. The local client itself has no retries — it forwards to the upstream provider once.

## Pattern 6: Connection-down detection

```python
def workerllm_available() -> bool:
    """Quick liveness check; useful at app startup."""
    import requests
    try:
        url = os.environ.get("JOHN_LLM_CLIENT_URL", "http://localhost:8500") + "/healthz"
        return requests.get(url, timeout=2).status_code == 200
    except Exception:
        return False
```

Use this at produced-app startup to fail-loud if the server isn't running, rather than crashing on the first real call.
