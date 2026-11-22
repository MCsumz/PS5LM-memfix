#!/usr/bin/env python3
"""PS5LM model test: one short, repeatable check per model, run against the loaded one.

    scripts/ps5lm-modeltest.py <PS5 address> [--ftp-port 2121] [--out DIR] [--skip live,speed]

It checks what decides whether a model is usable for long agent chats on the console:

  info      the loaded model, its plan (context, cache), load time and memory when ready (app.log)
  template  whether the chat template keeps earlier turns' thinking, renders empty thinking blocks,
            and keeps an agent turn's prompt as a prefix of the next user message's prompt, for a
            client that sends the thinking back and one that does not (Open WebUI without a
            provider). A turn that is not kept is read again in full: what patches/0012 fixed for
            Qwen3.5.
  live      one agent turn with a read_file tool, sent as Open WebUI sends it, then the same
            follow-up three times, then three times with preserve_reasoning off: the tokens each
            processed, whether its visible reply is empty and whether it hit the token limit
  speed     prompt and generation speed for a fixed 1,500-word prompt and 256 tokens (issue #6)
  memory    the pool and heap after the test (app.log)

Only standard Python 3. It sends chat requests to your own PS5 and reads its logs; it changes
nothing on the console. Results go to <out>/<model>.json and a short summary is printed.
"""
import argparse
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DOCS = ['docs/BUILDING.md', 'CHANGELOG.md', 'README.md']


class Server:
    def __init__(self, host, port, ftp_port):
        self.base = f'http://{host}:{port}'
        self.ftp = f'ftp://{host}:{ftp_port}'

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=30) as r:
            return json.load(r)

    def post(self, path, body, timeout=1800):
        req = urllib.request.Request(self.base + path, json.dumps(body).encode(),
                                     {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    def log(self, name):
        try:
            with urllib.request.urlopen(f'{self.ftp}/data/PS5LM/{name}', timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        except (urllib.error.URLError, OSError):
            return ''


def info(s):
    props = s.get('/props')
    path = props.get('model_path', '')
    model = path.rsplit('/', 1)[-1]
    out = {'model': model, 'n_ctx': props['default_generation_settings']['n_ctx'],
           'modalities': {k: v for k, v in props.get('modalities', {}).items() if v},
           'preserve_reasoning': props.get('chat_template_caps', {}).get('supports_preserve_reasoning')}
    log = s.log('app.log')
    plan = [l for l in log.splitlines() if f'ps5lm-app: model {model} ' in l]
    ready = [l for l in log.splitlines() if 'memory when ready' in l]
    if plan:
        out['plan'] = plan[-1].split(f'{model} ', 1)[1]
    if ready:
        out['ready'] = re.sub(r', Vulkan0.*', '', ready[-1].split('memory when ready: ', 1)[1])
    # from the server's arguments to memory when ready; the library lists every model's plan
    # at start, so the plan line is not when the load began
    start = [l for l in log.splitlines() if re.search(r'\d\d:\d\d:\d\d ps5lm-app: arg ', l)]
    clock = lambda l: sum(int(x) * m for x, m in zip(re.search(r'(\d\d:\d\d:\d\d) ps5lm-app', l).group(1).split(':'),
                                                      (3600, 60, 1)))
    if start and ready:
        seconds = clock(ready[-1]) - clock(start[-1])
        if 0 <= seconds < 3600:
            out['load_seconds'] = seconds
    return out


def template(s):
    """Prompt stability across a new user message, by rendering only: nothing is generated."""
    def render(messages, prompt=True):
        return s.post('/apply-template', {'messages': messages, 'add_generation_prompt': prompt})['prompt']

    def ntok(text):
        return len(s.post('/tokenize', {'content': text})['tokens'])

    out = {}
    u1, u2 = {'role': 'user', 'content': 'Question one'}, {'role': 'user', 'content': 'Question two'}
    kept = render([u1, {'role': 'assistant', 'content': 'Answer one', 'reasoning_content': 'thinking one'}, u2])
    out['earlier_thinking_kept'] = 'thinking one' in kept
    bare = render([u1, {'role': 'assistant', 'content': 'Answer one'}, u2])
    head = bare[:bare.index('Answer one')][-60:]
    out['empty_block_for_bare_turn'] = bool(re.search(r'think|thought', head, re.I))

    call = {'id': 'c1', 'type': 'function', 'function': {'name': 'read_file', 'arguments': '{"path": "a.txt"}'}}
    for client, reasoning in (('sends_thinking_back', {'reasoning_content': 'I should read a.txt.'}),
                              ('sends_no_thinking', {})):
        turn = [{'role': 'system', 'content': 'You have a read_file tool.'}, u1,
                {'role': 'assistant', 'content': '', 'tool_calls': [call], **reasoning},
                {'role': 'tool', 'tool_call_id': 'c1', 'content': 'The file says hello. ' * 40}]
        last = render(turn)                                    # the turn's last request
        final = {'role': 'assistant', 'content': 'It says hello.', **reasoning}
        nxt = render(turn + [final, u2])                       # the next user message
        common = next((i for i, (a, b) in enumerate(zip(last, nxt)) if a != b), min(len(last), len(nxt)))
        out[client] = {'turn_tokens': ntok(last), 'kept_tokens': ntok(last[:common]),
                       'kept_share': round(ntok(last[:common]) / max(1, ntok(last)), 3)}
    return out


def live(s, tools_files):
    """One agent turn as Open WebUI sends it (no thinking back), then three equal follow-ups."""
    tool = [{'type': 'function', 'function': {
        'name': 'read_file', 'description': 'Read a file of the PS5LM repository.',
        'parameters': {'type': 'object', 'properties': {'path': {'type': 'string', 'enum': list(tools_files)}},
                       'required': ['path']}}}]

    def chat(messages, **extra):
        t = time.time()
        r = s.post('/v1/chat/completions', {'messages': messages, 'tools': tool, 'max_tokens': 3000, **extra})
        m, tm = r['choices'][0]['message'], r.get('timings', {})
        return m, {'processed': tm.get('prompt_n'), 'cached': tm.get('cache_n'),
                   'prompt_s': round(tm.get('prompt_ms', 0) / 1000, 1), 'seconds': round(time.time() - t, 1),
                   'visible_chars': len((m.get('content') or '').strip()),
                   'thinking_chars': len(m.get('reasoning_content') or ''),
                   'cut_off': r['choices'][0].get('finish_reason') == 'length'}

    # an empty reply that ran into max_tokens was still thinking: the limit, not the model
    empty = lambda replies: sum(f['visible_chars'] == 0 and not f['cut_off'] for f in replies)

    messages = [{'role': 'system', 'content': 'You are a coding assistant. Use read_file, one call at a time.'},
                {'role': 'user', 'content': 'Read ' + ', '.join(tools_files) + ' one after another with '
                                            'read_file, then say in three sentences what PS5LM is.'}]
    steps = []
    for _ in range(6):
        m, t = chat(messages)
        steps.append(t)
        calls = m.get('tool_calls') or []
        messages.append({'role': 'assistant', 'content': m.get('content') or '', **({'tool_calls': calls} if calls else {})})
        if not calls:
            break
        for c in calls:
            try:
                path = json.loads(c['function']['arguments']).get('path', '')
            except json.JSONDecodeError:
                path = ''
            text = (ROOT / path).read_text()[:12000] if path in tools_files else 'no such file'
            messages.append({'role': 'tool', 'tool_call_id': c['id'], 'content': text})
    messages.append({'role': 'user', 'content': 'Thanks. Without tools, in two sentences: what is the '
                                                'keep-alive fix about?'})
    follow = [chat(messages, max_tokens=4000)[1] for _ in range(3)]
    # the same follow-ups with preserve_reasoning off. Where the prompt is the same either way (a
    # client that sends no thinking back, with patches/0012), these read 4 tokens and any empty
    # replies are the model's own; where it differs, the setting changes what the model sees
    off = [chat(messages, max_tokens=4000, chat_template_kwargs={'preserve_reasoning': False})[1]
           for _ in range(3)]
    return {'agent_steps': steps, 'tool_calls': len(steps) - 1, 'follow_ups': follow,
            'empty_visible': empty(follow), 'cut_off': sum(f['cut_off'] for f in follow),
            'follow_ups_preserve_off': off, 'empty_visible_preserve_off': empty(off)}


def speed(s):
    text = (ROOT / 'docs/BUILDING.md').read_text()
    words = text.split()
    prompt = ' '.join((words * 4)[:1500])
    r = s.post('/completion', {'prompt': prompt, 'n_predict': 256, 'ignore_eos': True, 'cache_prompt': False,
                               'temperature': 0.6})
    tm = r['timings']
    return {'prompt_tokens': tm['prompt_n'], 'prompt_tps': round(tm['prompt_per_second'], 1),
            'gen_tokens': tm['predicted_n'], 'gen_tps': round(tm['predicted_per_second'], 1)}


def memory(s):
    lines = [l for l in s.log('app.log').splitlines() if 'memory after request' in l]
    return lines[-1].split('request ', 1)[1] if lines else None


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('host')
    p.add_argument('--port', type=int, default=8081)
    p.add_argument('--ftp-port', type=int, default=2121)
    p.add_argument('--out', type=Path, default=ROOT / 'build/model-tests')
    p.add_argument('--skip', default='', help='comma-separated parts to skip: template, live, speed')
    a = p.parse_args()
    s, skip = Server(a.host, a.port, a.ftp_port), set(filter(None, a.skip.split(',')))
    result = {'when': time.strftime('%Y-%m-%d %H:%M'), 'info': info(s)}
    print(json.dumps(result['info'], indent=1), flush=True)
    for name, fn in (('template', lambda: template(s)), ('live', lambda: live(s, DOCS)), ('speed', lambda: speed(s))):
        if name not in skip:
            try:
                result[name] = fn()
            except Exception as e:  # a model that fails one part still gets the others
                result[name] = {'error': f'{type(e).__name__}: {e}'}
            print(name, json.dumps(result[name], indent=1), flush=True)
    result['memory_after'] = memory(s)
    print('memory', result['memory_after'])
    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out / (Path(result['info']['model']).stem + '.json')
    path.write_text(json.dumps(result, indent=2) + '\n')
    print('saved', path)


if __name__ == '__main__':
    main()
