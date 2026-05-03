"""LLM client: OpenAI-compatible /v1/chat/completions (works with both
llama-server and Ollama). Multi-host pool, each host = 1 slot."""
from __future__ import annotations
import json
import urllib.request
import urllib.error
import os
import threading
import queue
import time


# LLM_HOSTS is the new env name; OLLAMA_HOSTS kept for backward compat.
_HOSTS_ENV = os.environ.get('LLM_HOSTS', os.environ.get('OLLAMA_HOSTS', os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:8080')))
OLLAMA_HOSTS = [h.strip() for h in _HOSTS_ENV.split(',') if h.strip()]
MODEL_NAME = os.environ.get('MODEL', 'default')


class _HostPool:
    """Bounded pool of host URLs. acquire() blocks until a host is free."""
    def __init__(self, hosts: list[str]):
        self.hosts = list(hosts)
        self._q: queue.Queue = queue.Queue()
        for h in self.hosts:
            self._q.put(h)
        self.fail_count: dict[str, int] = {h: 0 for h in self.hosts}
        self.req_count: dict[str, int] = {h: 0 for h in self.hosts}
        self._lock = threading.Lock()

    def acquire(self, timeout: float | None = None) -> str:
        return self._q.get(timeout=timeout)

    def release(self, host: str):
        self._q.put(host)

    def mark_fail(self, host: str):
        with self._lock:
            self.fail_count[host] += 1

    def mark_ok(self, host: str):
        with self._lock:
            self.req_count[host] += 1

    def stats(self) -> dict:
        with self._lock:
            return {
                'req': dict(self.req_count),
                'fail': dict(self.fail_count),
                'pool_size': len(self.hosts),
            }


pool = _HostPool(OLLAMA_HOSTS)


class LLMError(Exception):
    pass


def _post_chat(host: str, body: dict, timeout: int = 300) -> str:
    """OpenAI-compatible /v1/chat/completions (works with llama-server + Ollama)."""
    url = f'{host}/v1/chat/completions'
    req = urllib.request.Request(
        url, data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode('utf-8'))
        return data['choices'][0]['message']['content']


NUM_CTX = int(os.environ.get('NUM_CTX', '4096'))


def chat(messages: list[dict], model: str = MODEL_NAME,
         temperature: float = 0.8, max_tokens: int = 400,
         response_format: str | None = None,
         disable_thinking: bool = True,
         timeout: int = 300) -> str:
    """Acquire a free host, send chat, release. Fails over to other hosts on error."""
    if disable_thinking and messages and messages[0]['role'] == 'system':
        if '/no_think' not in messages[0]['content']:
            messages = [dict(messages[0], content=messages[0]['content'] + '\n\n/no_think')] + messages[1:]
    body = {
        'model': model,
        'messages': messages,
        'stream': False,
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    if response_format == 'json':
        body['response_format'] = {'type': 'json_object'}

    last_err: Exception | None = None
    tried: set[str] = set()
    # At most try every host once (failover)
    for _ in range(len(pool.hosts)):
        host = pool.acquire()
        if host in tried:
            pool.release(host)
            continue
        tried.add(host)
        try:
            content = _post_chat(host, body, timeout=timeout)
            pool.mark_ok(host)
            pool.release(host)
            import re
            return re.sub(r'<think>.*?</think>\s*', '', content, flags=re.DOTALL).strip()
        except urllib.error.HTTPError as e:
            pool.mark_fail(host)
            pool.release(host)
            last_err = LLMError(f'HTTP {e.code} from {host}: {e.read().decode(errors="replace")[:200]}')
        except Exception as e:
            pool.mark_fail(host)
            pool.release(host)
            last_err = LLMError(f'{host}: {e}')

    raise last_err or LLMError('all hosts failed')


def simple_prompt(system: str, user: str, **kwargs) -> str:
    return chat([
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': user},
    ], **kwargs)


def warmup_all() -> dict:
    """Ping every host in parallel so each loads the model."""
    import concurrent.futures as cf
    results = {}
    def _ping(h):
        t0 = time.time()
        try:
            content = _post_chat(h, {
                'model': MODEL_NAME,
                'messages': [
                    {'role': 'system', 'content': 'Reply with just OK.\n\n/no_think'},
                    {'role': 'user', 'content': 'ping'},
                ],
                'stream': False,
                'temperature': 0.1,
                'max_tokens': 8,
            })
            return (h, True, time.time() - t0, content[:40])
        except Exception as e:
            return (h, False, time.time() - t0, str(e)[:80])

    with cf.ThreadPoolExecutor(max_workers=len(pool.hosts)) as ex:
        for r in ex.map(_ping, pool.hosts):
            results[r[0]] = {'ok': r[1], 'sec': round(r[2], 1), 'msg': r[3]}
    return results


if __name__ == '__main__':
    print(f'Model: {MODEL_NAME}')
    print(f'Hosts: {OLLAMA_HOSTS}')
    print(f'Warmup: {warmup_all()}')
