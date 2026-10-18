"""Deterministic T2/T3/T4 doubles for T5 only: no network or durable database."""

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from .routing import verified_direct

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / 'fixtures' / 'contracts' / f'{name}.json').read_text())


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def instant(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def demo_events():
    """Already normalized, synthetic events; this is not webhook verification."""
    target = fixture('incoming_message')
    events = []
    for previous in fixture('interpretation_request')['recent_messages']:
        events.append(dict(target, message_id=previous['message_id'],
                           sender_id=previous['sender_id'], sent_at=previous['sent_at'],
                           text=previous['text'], kind='text', sticker=None))
    return events + [target]


class MockStore:
    """Process-local T4 stand-in. Keeping this object is not database recovery."""

    def __init__(self):
        request = fixture('interpretation_request')
        self.routes = [{
            'platform': request['platform'], 'conversation_id': request['conversation_id'],
            'recipient_id': request['recipient_id'], 'destination': 'demo-private-assistant-thread',
            'enabled': True, 'members': [request['recipient_id'], request['sender_id']],
        }]
        self.profiles = {request['recipient_id']: copy.deepcopy(request['user_context'])}
        self.history = []
        self.seen = {}
        self.jobs = {}
        self.index = {}
        self.feedback = []  # Deliberately never retrieved into requests.
        self.observed_settings = []

    def observe(self, event, settings):
        self.observed_settings.append(copy.deepcopy(settings))
        routes = [r for r in self.routes if r['platform'] == event['platform']
                  and r['conversation_id'] == event['conversation_id'] and r['enabled']
                  and event['sender_id'] in r['members']]
        if not routes:
            return []
        key = (event['platform'], event['conversation_id'], event['message_id'])
        serialized = canonical(event)
        if key in self.seen and self.seen[key] != serialized:
            raise ValueError('Existing message identity has different content')
        if key not in self.seen:
            self.seen[key] = serialized
            self.history.append(copy.deepcopy(event))
        if event['kind'] != 'sticker':
            return []
        ids = []
        for route in routes:
            if route['recipient_id'] == event['sender_id'] and not verified_direct(route):
                continue
            job_key = (*key, route['recipient_id'])
            if job_key not in self.index:
                request = self._request(event, route, settings)
                window_id = len(self.jobs) + 1
                self.index[job_key] = window_id
                self.jobs[window_id] = {
                    'window_id': window_id, 'state': 'pending', 'result': None,
                    'request': request,
                    'request_sha256': hashlib.sha256(canonical(request).encode()).hexdigest(),
                    'idempotency_key': hashlib.sha256(canonical(job_key).encode()).hexdigest(),
                    'receipt': None, 'errors': [],
                }
            ids.append(self.index[job_key])
        return ids

    def _request(self, event, route, settings):
        # Emulate the agreed T4 behavior for test inputs only; no production store.
        earlier = []
        for item in self.history:
            if item['platform'] == event['platform'] and item['conversation_id'] == event['conversation_id']:
                if item['message_id'] == event['message_id']:
                    break
                if instant(item['sent_at']) <= instant(event['sent_at']):
                    earlier.append(item)
        earlier.sort(key=lambda item: instant(item['sent_at']))
        earlier = earlier[-settings['context_message_limit']:]
        remaining = settings['context_text_character_budget']
        recent = []
        for item in reversed(earlier):
            text = item['text']
            clipped = None if text is None else text[:min(settings['message_text_character_limit'], remaining)]
            if clipped is not None:
                remaining -= len(clipped)
            recent.append({
                'message_id': item['message_id'], 'sender_id': item['sender_id'],
                'sent_at': item['sent_at'], 'text': clipped,
                'text_truncated': text is not None and text != clipped,
                'kind': item['kind'], 'media_not_interpreted': item['kind'] != 'text',
                'reply_to_message_id': item['reply_to_message_id'],
            })
        text = event['text']
        clipped = None if text is None else text[:settings['target_text_character_limit']]
        profile = self.profiles.get(route['recipient_id'], {
            'preferences': {'language': settings['language'], 'explanation_length': settings['explanation_length']},
            'preferences_source': 'default', 'relationship': None, 'relationship_source': None,
        })
        return {
            'schema_version': 2, 'policy_version': 'context-v1',
            'source_message_id': event['message_id'], 'platform': event['platform'],
            'conversation_id': event['conversation_id'], 'sender_id': event['sender_id'],
            'recipient_id': route['recipient_id'], 'sent_at': event['sent_at'],
            'target_text': clipped, 'target_text_truncated': text is not None and text != clipped,
            'reply_to_message_id': event['reply_to_message_id'], 'sticker': copy.deepcopy(event['sticker']),
            'recent_messages': list(reversed(recent)),
            'context_message_limit': settings['context_message_limit'],
            'context_text_character_budget': settings['context_text_character_budget'],
            'context_age_limit': None, 'user_context': copy.deepcopy(profile),
        }

    def load_job(self, window_id):
        return copy.deepcopy(self.jobs[window_id])

    def resolve_route(self, window_id):
        request = self.jobs[window_id]['request']
        for route in self.routes:
            if all(route[key] == request[key] for key in ('platform', 'conversation_id', 'recipient_id')):
                return copy.deepcopy(route)
        raise PermissionError('No active enrollment')

    def claim(self, window_id, phase):
        job = self.jobs[window_id]
        if job['state'] in ('accepted', 'sending', 'interpreting', 'delivery_unknown'):
            return False
        job['state'] = phase
        return True

    def save_result(self, window_id, result):
        self.jobs[window_id]['result'] = copy.deepcopy(result)
        self.jobs[window_id]['state'] = 'interpreted'

    def mark_failure(self, window_id, state, error_code):
        self.jobs[window_id]['state'] = state
        self.jobs[window_id]['errors'].append(error_code)

    def mark_accepted(self, window_id, receipt):
        self.jobs[window_id]['receipt'] = copy.deepcopy(receipt)
        self.jobs[window_id]['state'] = 'accepted'


class MockInterpreter:
    """Return a fixed final v2 result; no image analysis or candidate inference."""

    def __init__(self, result_name='interpretation_result'):
        self.result_name = result_name
        self.calls = []
        self.failures_remaining = 0
        self.hook = None

    def __call__(self, request):
        self.calls.append(copy.deepcopy(request))
        if self.hook:
            self.hook(request)
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise TimeoutError('Synthetic model timeout')
        result = fixture(self.result_name)
        result['source_message_id'] = request['source_message_id']
        return result


class MockTransport:
    """Record fake provider acceptance. No socket, webhook, SMS or phone send."""

    def __init__(self):
        self.attempts = []
        self.receipts = {}
        self.rejections_remaining = 0
        self.timeout_after_accept = False
        self.hook = None

    def send_private(self, delivery, route, idempotency_key):
        self.attempts.append({'delivery': copy.deepcopy(delivery), 'route': copy.deepcopy(route),
                              'idempotency_key': idempotency_key})
        if self.hook:
            self.hook()
        if self.rejections_remaining:
            self.rejections_remaining -= 1
            return {'status': 'rejected'}
        receipt = self.receipts.setdefault(idempotency_key, {
            'status': 'accepted', 'provider_message_id': 'mock-' + idempotency_key[:12],
            'evidence': 'synthetic_provider_acceptance',
        })
        if self.timeout_after_accept:
            raise TimeoutError('Synthetic lost acknowledgment after acceptance')
        return copy.deepcopy(receipt)
