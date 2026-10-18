"""Offline composition of real components over explicitly synthetic provider I/O."""
import base64
import copy
import hashlib
import hmac
import json

from .adapters.assembly import Interpreter, PhotonTransport
from .adapters.photon import Attachment, PrivateDestination
from .adapters.vision import FixtureVision
from .context_store import SQLiteStore
from .main import create_pipeline
from .t5_mocks import demo_events, fixture

PROJECT, AGENT = 'synthetic-project', 'synthetic-agent'
SYNTHETIC_KEY = b'offline-demo-signature-not-a-real-credential'


def sign(raw):
    return {'X-Synthetic-Signature': hmac.new(SYNTHETIC_KEY, raw, hashlib.sha256).hexdigest()}


def verify(raw, headers):
    return hmac.compare_digest(sign(raw)['X-Synthetic-Signature'],
                               headers.get('X-Synthetic-Signature', ''))


class CountingVision(FixtureVision):
    def __init__(self, candidate):
        super().__init__(candidate)
        self.calls = []

    def __call__(self, request):
        self.calls.append(copy.deepcopy(request))
        return super().__call__(request)


class SyntheticProvider:
    def __init__(self):
        self.assets, self.sends, self.receipts = {}, [], {}
        self.send_error = None

    def fetch_attachment(self, attachment_id, *, max_bytes, timeout):
        return Attachment(self.assets[attachment_id], 'image/png')

    def send_message(self, body, *, idempotency_key, timeout):
        self.sends.append((copy.deepcopy(body), idempotency_key))
        if self.send_error:
            raise self.send_error
        return self.receipts.setdefault(idempotency_key,
            {'id': 'synthetic-' + str(len(self.receipts) + 1), 'status': 'accepted'})


def envelope(event, provider):
    if event['kind'] == 'sticker':
        attachment_id = 'synthetic-attachment-' + event['message_id']
        provider.assets[attachment_id] = base64.b64decode(event['sticker']['data_base64'])
        content = {'type': 'attachment', 'attachmentId': attachment_id,
                   'metadata': {'synthetic_kind': 'sticker'}}
        if event['text']:
            content = {'type': 'group', 'parts': [
                {'type': 'text', 'text': event['text']}, content]}
    else:
        content = {'type': 'text', 'text': event['text'] or ''}
    return json.dumps({'synthetic_message': {
        'id': event['message_id'], 'projectId': PROJECT, 'platform': event['platform'],
        'status': 'received', 'sentBy': {'id': event['sender_id'],
            'projectId': PROJECT, 'platform': event['platform']},
        'space': {'id': event['conversation_id'], 'projectId': PROJECT, 'platform': event['platform']},
        'timestamps': {'receivedAt': event['sent_at']}, 'content': content,
        'parentMessageId': event['reply_to_message_id'],
    }}).encode()


def build_demo(path, case='single', direct=False):
    events = demo_events()
    target = events[-1]
    recipient = fixture('interpretation_request')['recipient_id']
    if direct:
        for event in events:
            event['sender_id'] = recipient
    store = SQLiteStore(path)
    members = [recipient, AGENT] if direct else [recipient, target['sender_id']]
    destination = target['conversation_id'] if direct else 'demo-private-assistant-thread'
    store.enroll(target['platform'], target['conversation_id'], recipient, destination, members,
                 source_kind='direct' if direct else 'group', source_verified=direct,
                 assistant_id=AGENT if direct else None)
    provider = SyntheticProvider()

    def private(delivery, route):
        # Explicit fictional binding only. A live resolver must verify actual participants.
        return PrivateDestination(delivery['recipient_id'], delivery['source_conversation_id'],
            target['platform'], route['destination'], AGENT, recipient,
            (AGENT, recipient), verified=True)

    transport = PhotonTransport(store, project_id=PROJECT, platform=target['platform'],
        assistant_ids=[AGENT], client=provider, verify_event=verify,
        decode_event=lambda body: body.get('synthetic_message'), resolve_private=private,
        classify_attachment=lambda message, part: part.get('metadata', {}).get('synthetic_kind', 'other'))
    vision = CountingVision(fixture('candidate_' + case))
    pipeline = create_pipeline(store, Interpreter(vision), transport)
    return store, pipeline, transport, provider, vision, events


def run_demo(path, case='single', replay=False, direct=False):
    store, pipeline, transport, provider, vision, events = build_demo(path, case, direct)
    try:
        receipts = []
        for event in events + ([events[-1]] if replay else []):
            raw = envelope(event, provider)
            receipts.append(transport.receive_webhook(raw, sign(raw), pipeline).status)
        jobs = [store.load_job(row['window_id']) for row in
                store.db.execute('SELECT window_id FROM pipeline_jobs ORDER BY window_id').fetchall()]
        return {'mode': 'fixture', 'interpretation_is_fixed_fixture': True,
            'network_calls': 0, 'phone_delivery_verified': False, 'durable_store_implemented': True,
            'source_mode': 'direct' if direct else 'group', 'ingress': receipts,
            'model_calls_mocked': len(vision.calls), 'provider_sends_mocked': len(provider.sends),
            'windows': [{'window_id': j['window_id'], 'state': j['state'],
                         'request_sha256': j['request_sha256']} for j in jobs]}
    finally:
        store.close()
