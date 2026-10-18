"""Real T2/T3/T4/T5 composition, with synthetic provider I/O and no sockets."""
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.demo import build_demo, envelope, sign
from src.main import run_window
from src.adapters.photon import PhotonError, PrivateDestination


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.guard = patch.object(socket, 'socket', side_effect=AssertionError('Network forbidden'))
        self.guard.start()
        self.addCleanup(self.guard.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'assembly.sqlite3'
        self.configure()

    def configure(self, case='single', direct=False):
        (self.store, self.pipeline, self.transport, self.provider,
         self.vision, self.events) = build_demo(self.path, case, direct)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def receive(self, event=None, headers=None):
        raw = envelope(event or self.events[-1], self.provider)
        return self.transport.receive_webhook(raw, sign(raw) if headers is None else headers, self.pipeline)

    def test_real_components_send_once_after_image_and_policy_validation(self):
        for event in self.events:
            self.assertEqual(self.receive(event).status, 'forwarded')
        self.assertEqual(self.store.load_job(1)['state'], 'accepted')
        self.assertEqual(len(self.vision.calls), 1)
        self.assertEqual(len(self.provider.sends), 1)
        receipt = self.store.load_job(1)['receipt']
        self.assertEqual(receipt['provider_idempotency_key'], self.provider.sends[0][1])
        self.assertEqual(self.vision.calls[0]['interpreter']['provider'], 'fixture')
        self.assertNotIn('destination', self.vision.calls[0])

    def test_unauthenticated_raw_event_never_reaches_the_store(self):
        self.assertEqual(self.receive(headers={}).status, 'rejected')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM messages').fetchone()[0], 0)
        self.assertEqual(self.vision.calls, [])

    def test_replay_after_restart_uses_saved_receipt(self):
        self.receive()
        self.store.close()
        self.configure()
        self.receive()
        self.assertEqual(self.store.load_job(1)['state'], 'accepted')
        self.assertEqual(self.vision.calls, [])
        self.assertEqual(self.provider.sends, [])

    def test_compatible_and_opposing_policy_survives_assembly(self):
        for case, alternative in [('compatible', True), ('opposing', False)]:
            with self.subTest(case=case):
                event = dict(self.events[-1], message_id=case)
                self.pipeline['interpreter'].vision.result = json.loads(
                    (Path(__file__).resolve().parents[1] / f'fixtures/contracts/candidate_{case}.json').read_text())
                self.receive(event)
                job = self.store.load_job(len(self.provider.sends))
                self.assertEqual(bool(job['result']['alternative']), alternative)
                self.assertTrue(job['result']['uncertainty_caveat'])

    def test_timeout_becomes_unknown_and_explicit_retry_does_not_resend(self):
        self.provider.send_error = TimeoutError('synthetic lost acknowledgment')
        self.receive()
        self.assertEqual(self.store.load_job(1)['state'], 'delivery_unknown')
        self.assertEqual(run_window(self.pipeline, 1, retry=True)['status'], 'reconciliation_required')
        self.assertEqual(len(self.provider.sends), 1)

    def test_definite_rate_rejection_retries_with_same_provider_key(self):
        self.provider.send_error = PhotonError('provider_http_429', retryable=True)
        self.receive()
        self.assertEqual(self.store.load_job(1)['state'], 'send_failed')
        self.provider.send_error = None
        self.assertEqual(run_window(self.pipeline, 1, retry=True)['status'], 'accepted')
        self.assertEqual(len(self.vision.calls), 1)
        self.assertEqual(self.provider.sends[0][1], self.provider.sends[1][1])

    def test_wrong_external_private_binding_is_rejected_before_send(self):
        def wrong(delivery, route):
            return PrivateDestination(delivery['recipient_id'], delivery['source_conversation_id'],
                self.events[-1]['platform'], 'different-private-thread', 'synthetic-agent',
                delivery['recipient_id'], ('synthetic-agent', delivery['recipient_id']), verified=True)
        self.transport.resolve_private = wrong
        self.receive()
        self.assertEqual(self.store.load_job(1)['state'], 'send_failed')
        self.assertEqual(self.provider.sends, [])

    def test_verified_direct_source_uses_the_same_private_thread(self):
        self.store.close()
        self.configure(direct=True)
        self.receive()
        self.assertEqual(self.store.load_job(1)['state'], 'accepted')
        self.assertEqual(self.provider.sends[0][0]['spaceId'], self.events[-1]['conversation_id'])


if __name__ == '__main__':
    unittest.main()
