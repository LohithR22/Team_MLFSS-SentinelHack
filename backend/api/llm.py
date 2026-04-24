from rest_framework.decorators import api_view
from rest_framework.response import Response

from llm import loader as llm_loader


@api_view(['GET'])
def status(_request):
    """Report loader state without forcing a download."""
    return Response({
        'loaded': llm_loader.is_loaded(),
        'default_model': llm_loader.DEFAULT_MODEL_ID,
    })


@api_view(['POST', 'GET'])
def test(request):
    """Smoke endpoint: triggers model load on first call.

    GET  /api/llm/test/                   → default prompt
    POST /api/llm/test/ {"prompt": "..."} → custom prompt
    """
    prompt = (request.data or {}).get('prompt') if request.method == 'POST' else None
    prompt = prompt or request.query_params.get('prompt') or 'Reply with just the word: READY'
    try:
        reply = llm_loader.generate(
            [
                {'role': 'system', 'content': 'You are a concise assistant.'},
                {'role': 'user',   'content': prompt},
            ],
            max_new_tokens=64,
        )
    except Exception as e:
        return Response(
            {'error': f'{type(e).__name__}: {e}',
             'hint': 'Run `huggingface-cli login` and request access to '
                     'meta-llama/Llama-3.2-1B-Instruct if this is the first run.'},
            status=500,
        )
    llm = llm_loader.get_llm()
    return Response({
        'model_id': llm.model_id,
        'device': llm.device,
        'dtype': llm.dtype,
        'prompt': prompt,
        'reply': reply,
    })
