"""Real SQLite/Jac scheduling with fake model and transport; no network access."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.context_store import SQLiteStore
from src.main import create_pipeline, load_settings, process_event, run_window
from src.repository import purge_conversation
from src.t5_mocks import MockInterpreter, MockTransport, demo_events


class ContextStoreTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(socket, 'socket', side_effect=AssertionError('Network forbidden'))
        guard.start()
        self.addCleanup(guard.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'store.sqlite3'
        self.store = SQLiteStore(self.path)
        self.events = demo_events()
        self.target = self.events[-1]
        self.recipient = 'demo-older-recipient'
        self.enroll()
        self.model, self.transport = MockInterpreter(), MockTransport()
        self.pipeline = create_pipeline(self.store, self.model, self.transport)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def enroll(self, **kwargs):
        self.store.enroll(self.target['platform'], self.target['conversation_id'],
            self.recipient, kwargs.pop('destination', 'private-thread'),
            kwargs.pop('members', [self.recipient, self.target['sender_id']]), **kwargs)

    def process(self, target=None):
        return process_event(self.pipeline, target or self.target, authenticated=True)[0]

    def prepare(self):
        for event in self.events[:-1]:
            self.store.observe(event, self.pipeline['settings'])
        return self.store.observe(self.target, self.pipeline['settings'])[0]

    def restart(self):
        self.store.close()
        self.store = SQLiteStore(self.path)
        self.pipeline = create_pipeline(self.store, self.model, self.transport)

    def test_complete_pipeline_persists_provider_acceptance_and_one_outbox(self):
        self.prepare()
        self.assertEqual(self.process()['status'], 'accepted')
        self.assertEqual(self.store.load_job(1)['state'], 'accepted')
        row = self.store.db.execute('SELECT * FROM outbox').fetchone()
        self.assertEqual(row['status'], 'accepted')
        self.assertTrue(json.loads(row['receipt_json'])['provider_message_id'])
        self.assertEqual(len(self.model.calls), 1)
        self.assertEqual(len(self.transport.attempts), 1)

    def test_restart_and_replay_do_not_repeat_model_or_send(self):
        self.process()
        snapshot = self.store.load_job(1)
        self.restart()
        self.assertEqual(self.process()['status'], 'already_accepted')
        self.assertEqual(self.store.load_job(1), snapshot)
        self.assertEqual(len(self.model.calls), 1)
        self.assertEqual(len(self.transport.attempts), 1)

    def test_frozen_window_survives_later_settings_and_history(self):
        self.prepare()
        before = self.store.load_job(1)['request']
        later = dict(self.target, message_id='later', kind='text', sticker=None, text='later')
        self.store.observe(later, self.pipeline['settings'])
        self.store.set_preferences(self.target['platform'], self.recipient, 'es', 'detailed')
        self.store.set_relationship(self.target['platform'], self.recipient, self.target['sender_id'], 'friend')
        self.restart()
        self.assertEqual(self.store.load_job(1)['request'], before)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.db.execute("UPDATE context_windows SET request_json='{}' WHERE id=1")
        self.store.db.rollback()

    def test_long_history_bounded_window_old_messages_and_future_exclusion(self):
        for i in range(30):
            event = dict(self.target, message_id=f'old-{i}', kind='text', sticker=None,
                text=f'old {i}', sent_at=(datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=i)).isoformat())
            self.store.observe(event, self.pipeline['settings'])
        self.store.observe(dict(event, message_id='future', sent_at='2030-01-01T00:00:00Z'), self.pipeline['settings'])
        self.prepare()
        recent = self.store.load_job(1)['request']['recent_messages']
        self.assertEqual(len(recent), 25)
        self.assertNotIn('future', [m['message_id'] for m in recent])
        self.assertTrue(any(m['sent_at'].startswith('2020') for m in recent))
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM messages').fetchone()[0], 34)

    def test_reused_image_has_separate_job_but_changed_identity_is_rejected(self):
        self.process()
        self.process(dict(self.target, message_id='different-message'))
        self.assertEqual(len(self.model.calls), 2)
        with self.assertRaises(ValueError):
            self.process(dict(self.target, text='changed body'))

    def test_paused_unenrolled_and_other_conversation_are_ignored(self):
        self.enroll(enabled=False)
        self.assertEqual(self.process()['status'], 'ignored_unenrolled_or_paused')
        self.enroll()
        self.assertEqual(self.process(dict(self.target, conversation_id='other'))['status'], 'ignored_unenrolled_or_paused')
        self.assertEqual(self.model.calls, [])

    def test_verified_direct_recipient_submission_replies_in_same_thread(self):
        self.enroll(destination=self.target['conversation_id'], members=[self.recipient, 'agent'],
                    source_kind='direct', source_verified=True, assistant_id='agent')
        target = dict(self.target, sender_id=self.recipient)
        self.assertEqual(self.process(target)['status'], 'accepted')
        self.assertEqual(self.transport.attempts[0]['route']['destination'], self.target['conversation_id'])

    def test_unverified_same_thread_and_group_destination_remain_forbidden(self):
        with self.assertRaises(ValueError):
            self.enroll(destination=self.target['conversation_id'])
        with self.assertRaises(ValueError):
            self.enroll(destination=self.target['conversation_id'], source_kind='direct')
        with self.assertRaises(ValueError):
            self.enroll(destination=self.target['conversation_id'], source_kind='direct',
                        source_verified=True, assistant_id='agent')

    def test_group_recipient_submission_is_still_skipped_and_echo_ignored(self):
        self.assertEqual(self.process(dict(self.target, sender_id=self.recipient))['status'], 'ignored_unenrolled_or_paused')
        self.assertEqual(self.process(dict(self.target, from_assistant=True))['status'], 'ignored_assistant')

    def test_explicit_model_retry_uses_original_snapshot(self):
        self.model.failures_remaining = 1
        self.assertEqual(self.process()['status'], 'interpretation_failed')
        before = self.store.load_job(1)['request']
        self.restart()
        self.assertEqual(self.process()['status'], 'retry_required')
        self.assertEqual(run_window(self.pipeline, 1, retry=True)['status'], 'accepted')
        self.assertEqual(self.model.calls, [before, before])

    def test_send_retry_reuses_result_and_unknown_send_stays_blocked_after_restart(self):
        self.transport.rejections_remaining = 1
        self.assertEqual(self.process()['status'], 'send_failed')
        key = self.store.load_job(1)['idempotency_key']
        self.restart()
        self.assertEqual(run_window(self.pipeline, 1, retry=True)['status'], 'accepted')
        self.assertEqual(len(self.model.calls), 1)
        self.assertTrue(all(a['idempotency_key'] == key for a in self.transport.attempts))
        self.transport.timeout_after_accept = True
        self.process(dict(self.target, message_id='lost-ack'))
        self.restart()
        attempts = len(self.transport.attempts)
        self.assertEqual(run_window(self.pipeline, 2, retry=True)['status'], 'reconciliation_required')
        self.assertEqual(len(self.transport.attempts), attempts)

    def test_interrupted_claim_stays_reconciliation_required_after_restart(self):
        self.prepare()
        self.assertTrue(self.store.claim(1, 'interpreting'))
        self.restart()
        self.assertEqual(run_window(self.pipeline, 1, retry=True)['status'], 'reconciliation_required')
        self.assertEqual(self.model.calls, [])

    def test_two_database_connections_cannot_claim_same_phase(self):
        self.prepare()
        other = SQLiteStore(self.path)
        try:
            self.assertTrue(self.store.claim(1, 'interpreting'))
            self.assertFalse(other.claim(1, 'interpreting'))
        finally:
            other.close()

    def test_multiple_recipients_have_independent_durable_jobs(self):
        self.store.enroll(self.target['platform'], self.target['conversation_id'],
            'second-recipient', 'second-private', [self.target['sender_id'], 'second-recipient'])
        outcomes = process_event(self.pipeline, self.target, authenticated=True)
        self.assertEqual([o['status'] for o in outcomes], ['accepted', 'accepted'])
        self.assertEqual(len(self.model.calls), 2)
        self.assertEqual({a['delivery']['recipient_id'] for a in self.transport.attempts},
                         {self.recipient, 'second-recipient'})
        self.restart()
        self.assertEqual(self.store.load_job(2)['state'], 'accepted')

    def test_invalid_settings_roll_back_message_and_window_together(self):
        bad = dict(self.pipeline['settings'], context_message_limit=True)
        with self.assertRaises(ValueError):
            self.store.observe(self.target, bad)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM messages').fetchone()[0], 0)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM context_windows').fetchone()[0], 0)

    def test_legacy_queued_result_migrates_without_repeating_inference(self):
        self.process()
        with self.store.db:
            self.store.db.execute('DROP TABLE pipeline_jobs')
            self.store.db.execute("UPDATE interpretation_runs SET status='queued'")
            self.store.db.execute("UPDATE outbox SET status='pending', receipt_json=NULL")
        calls = len(self.model.calls)
        self.restart()
        self.assertEqual(self.store.load_job(1)['state'], 'interpreted')
        self.assertEqual(run_window(self.pipeline, 1)['status'], 'accepted')
        self.assertEqual(len(self.model.calls), calls)

    def test_saved_result_feedback_authorization_and_no_feedback_in_model_input(self):
        self.process()
        saved = self.store.get_explanation(1, self.recipient)
        self.assertNotIn('request', saved)
        self.assertNotIn('sticker', saved)
        with self.assertRaises(PermissionError):
            self.store.get_explanation(1, 'other')
        with self.assertRaises(PermissionError):
            self.store.save_feedback(1, 'other', 'first')
        with self.assertRaises(ValueError):
            self.store.save_feedback(1, self.recipient, 'second')
        result = self.store.save_feedback(1, self.recipient, 'first', 'private-choice-canary')
        self.assertEqual(result['feedback']['provenance'], 'recipient_judgment')
        self.process(dict(self.target, message_id='later-sticker'))
        self.assertNotIn('private-choice-canary', json.dumps(self.model.calls[-1]))
        self.assertNotIn('feedback', self.model.calls[-1]['user_context'])

    def test_unsupported_result_rejects_a_nonexistent_first_choice(self):
        self.model.result_name = 'result_unsupported'
        self.process()
        with self.assertRaises(ValueError):
            self.store.save_feedback(1, self.recipient, 'first')

    def test_truncation_budgets_and_conversation_purge(self):
        settings = dict(load_settings(), context_text_character_budget=50,
                        message_text_character_limit=40, target_text_character_limit=10)
        self.store.observe(dict(self.events[0], text='a' * 100), settings)
        self.store.observe(dict(self.events[1], text='b' * 100), settings)
        self.store.observe(dict(self.target, text='c' * 100), settings)
        request = self.store.load_job(1)['request']
        self.assertEqual(sum(len(m['text']) for m in request['recent_messages']), 50)
        self.assertEqual(request['target_text'], 'c' * 10)
        self.assertTrue(request['target_text_truncated'])
        purge_conversation(self.store.db, self.target['platform'], self.target['conversation_id'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM pipeline_jobs').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
