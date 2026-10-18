"""Browser view of the offline demo, served only on this machine.

The page is filled from the real coordinator, store, policy, and transport
boundaries. Model candidates and provider sends stay synthetic.
"""
import base64
import json
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .demo import build_demo, envelope, sign
from .t5_mocks import demo_events

LABELS = {
    'demo-older-recipient': 'Older recipient',
    'demo-younger-sender': 'Younger sender',
}
SCENES = (
    ('single', False, True, 'One meaning'),
    ('compatible', False, False, 'Compatible pair'),
    ('opposing', False, False, 'Opposing pair'),
    ('unsupported', False, False, 'Abstain'),
    ('single', True, True, 'Direct thread'),
)


def person(sender_id):
    return LABELS.get(sender_id, sender_id)


def sticker_png():
    media = demo_events()[-1]['sticker']
    data = base64.b64decode(media['data_base64'], validate=True)
    if media['mime_type'] != 'image/png' or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('Local demo sticker is not a PNG')
    return data


def run_case(case, direct, replay):
    with tempfile.TemporaryDirectory() as directory:
        store, pipeline, transport, provider, vision, events = build_demo(
            str(Path(directory) / 'demo.sqlite3'), case, direct)
        try:
            for event in events + ([events[-1]] if replay else []):
                raw = envelope(event, provider)
                transport.receive_webhook(raw, sign(raw), pipeline)
            if len(provider.sends) != 1 or len(vision.calls) != 1:
                raise RuntimeError('Local demo expected one interpretation and one send')
            request = store.load_job(1)['request']
            if 'feedback' in request:
                raise RuntimeError('Feedback must stay out of the interpretation request')
            body = provider.sends[0][0]
            return {
                'id': 'direct' if direct else case,
                'messages': [
                    {'sender_id': message['sender_id'], 'sender': person(message['sender_id']),
                     'text': message['text']}
                    for message in request['recent_messages']
                ],
                'sticker_sender': person(request['sender_id']),
                'explanation': body['content']['text'],
                'destination': body['spaceId'],
                'recipient': person(request['recipient_id']),
                'model_calls': len(vision.calls),
                'sends': len(provider.sends),
                'replayed': replay,
            }
        finally:
            store.close()


def collect_scenes():
    scenes = []
    for case, direct, replay, label in SCENES:
        scene = run_case(case, direct, replay)
        scene['label'] = label
        scenes.append(scene)
    return scenes, sticker_png()


def embed_json(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c')


def _page_markup():
    path = Path(__file__).with_name('local_demo_page.html')
    return path.read_text()


def render_page(scenes):
    return _page_markup().replace('__SCENES__', embed_json(scenes))


def serve(port=8765):
    scenes, png = collect_scenes()
    page = render_page(scenes).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path
            if path in ('/', '/index.html'):
                body, content_type = page, 'text/html; charset=utf-8'
            elif path == '/sticker.png':
                body, content_type = png, 'image/png'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            print('%s %s' % (self.address_string(), fmt % args), flush=True)

    server = None
    error = None
    for candidate in range(port, port + 10):
        try:
            server = ThreadingHTTPServer(('127.0.0.1', candidate), Handler)
            port = candidate
            break
        except OSError as caught:
            error = caught
    if server is None:
        raise error
    print('Local sticker demo: http://127.0.0.1:%s' % port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
