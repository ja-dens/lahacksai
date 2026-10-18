"""Real SQLite scheduling with fake model and transport; no network access."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch

from src.adapters.fetch_agent import FetchTools
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

    def test_fetch_feedback_command_replay_survives_store_and_agent_restart(self):
        self.process()
        arguments = {'window_id': 1, 'selection': 'first', 'note': 'Helpful.'}
        first = FetchTools(self.store).call('save_feedback', arguments,
            authenticated_recipient_id=self.recipient, command_id='sender:stable-message-id')
        self.restart()
        replay = FetchTools(self.store).call('save_feedback', arguments,
            authenticated_recipient_id=self.recipient, command_id='sender:stable-message-id')
        self.assertEqual(first, replay)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM feedback').fetchone()[0], 1)

    def test_durable_feedback_receipt_and_write_roll_back_together(self):
        self.process()
        with self.store.db:
            self.store.db.execute("CREATE TRIGGER reject_receipt BEFORE INSERT ON fetch_commands "
                                  "BEGIN SELECT RAISE(ABORT, 'simulated receipt failure'); END")
        tools = FetchTools(self.store)
        args = {'window_id': 1, 'selection': 'first'}
        with self.assertRaises(sqlite3.IntegrityError):
            tools.call('save_feedback', args, authenticated_recipient_id=self.recipient, command_id='atomic')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM feedback').fetchone()[0], 0)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM fetch_commands').fetchone()[0], 0)
        with self.store.db:
            self.store.db.execute('DROP TRIGGER reject_receipt')
        result = tools.call('save_feedback', args, authenticated_recipient_id=self.recipient, command_id='atomic')
        self.assertTrue(result['ok'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM feedback').fetchone()[0], 1)

    def test_durable_command_rejects_changed_payload_and_wrong_identity(self):
        self.process()
        tools = FetchTools(self.store)
        args = {'window_id': 1, 'selection': 'first'}
        first = tools.call('save_feedback', args, authenticated_recipient_id=self.recipient, command_id='same-id')
        self.restart()
        tools = FetchTools(self.store)
        for tool, arguments, recipient in (
            ('save_feedback', {**args, 'selection': 'neither'}, self.recipient),
            ('save_feedback', {**args, 'note': 'changed'}, self.recipient),
            ('get_explanation', {'window_id': 1}, self.recipient),
            ('save_feedback', {**args, 'window_id': True}, self.recipient),
            ('save_feedback', args, 'another-recipient'),
            ('save_feedback', {**args, 'recipient_id': self.recipient}, self.recipient),
        ):
            with self.subTest(tool=tool, arguments=arguments, recipient=recipient):
                denied = tools.call(tool, arguments, authenticated_recipient_id=recipient, command_id='same-id')
                self.assertFalse(denied['ok'])
        replay = tools.call('save_feedback', args, authenticated_recipient_id=self.recipient, command_id='same-id')
        self.assertEqual(first, replay)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM feedback').fetchone()[0], 1)

    def test_two_connections_share_one_durable_feedback_command(self):
        self.process()
        barrier = Barrier(2, timeout=5)

        def execute(_):
            other = SQLiteStore(self.path)
            try:
                barrier.wait()
                return FetchTools(other).call('save_feedback', {'window_id': 1, 'selection': 'first'},
                    authenticated_recipient_id=self.recipient, command_id='concurrent-command')
            finally:
                other.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(execute, range(2)))
        self.assertTrue(first['ok'])
        self.assertEqual(first, second)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM feedback').fetchone()[0], 1)

    def test_purge_removes_feedback_command_receipts_and_replay_access(self):
        self.process()
        tools = FetchTools(self.store)
        args = {'window_id': 1, 'selection': 'first'}
        self.assertTrue(tools.call('save_feedback', args,
            authenticated_recipient_id=self.recipient, command_id='purged')['ok'])
        purge_conversation(self.store.db, self.target['platform'], self.target['conversation_id'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM fetch_commands').fetchone()[0], 0)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM feedback').fetchone()[0], 0)
        replay = tools.call('save_feedback', args,
            authenticated_recipient_id=self.recipient, command_id='purged')
        self.assertEqual(replay, {'ok': False, 'error': 'Saved exchange unavailable.'})

    def test_invalid_feedback_has_no_durable_receipt(self):
        self.process()
        tools = FetchTools(self.store)
        args = {'window_id': 1, 'selection': 'second'}
        self.assertFalse(tools.call('save_feedback', args,
            authenticated_recipient_id=self.recipient, command_id='invalid')['ok'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM fetch_commands').fetchone()[0], 0)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM feedback').fetchone()[0], 0)

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

    def test_saved_result_leaves_a_durable_pending_outbox_without_sending(self):
        self.prepare()
        self.assertTrue(self.store.claim(1, 'interpreting'))
        result = self.model(self.store.load_job(1)['request'])
        self.store.save_result(1, result)
        self.restart()
        row = self.store.db.execute('SELECT * FROM outbox WHERE window_id=1').fetchone()
        self.assertEqual(row['status'], 'pending')
        self.assertIsNone(row['receipt_json'])
        self.assertEqual(self.store.load_job(1)['state'], 'interpreted')
        self.assertEqual(self.transport.attempts, [])
        self.assertEqual(len(self.model.calls), 1)
        self.assertEqual(self.store.get_explanation(1, self.recipient)['meaning'], result['meaning'])

    def test_lookup_and_feedback_deny_unknown_or_invalid_windows_identically(self):
        self.process()
        denials = []
        for window_id, recipient in ((1, 'other'), (999, self.recipient),
                (True, self.recipient), (1.0, self.recipient), ('1', self.recipient),
                (0, self.recipient), (1, '')):
            for operation in (
                lambda: self.store.get_explanation(window_id, recipient),
                lambda: self.store.save_feedback(window_id, recipient, 'first'),
            ):
                with self.assertRaises(PermissionError) as raised:
                    operation()
                denials.append(str(raised.exception))
        self.assertEqual(set(denials), {'Saved exchange unavailable.'})
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM feedback').fetchone()[0], 0)

    def test_second_feedback_choice_is_valid_only_for_a_shown_compatible_pair(self):
        self.model.result_name = 'result_compatible'
        self.process()
        saved = self.store.get_explanation(1, self.recipient)
        self.assertTrue(saved['alternative'])
        receipt = FetchTools(self.store).call('save_feedback', {'window_id': 1, 'selection': 'second'},
            authenticated_recipient_id=self.recipient, command_id='choose-second')
        self.assertEqual(receipt['feedback']['selection'], 'second')
        self.assertEqual(receipt['feedback']['provenance'], 'recipient_judgment')
        for selection in ('neither', 'not_sure'):
            self.assertEqual(self.store.save_feedback(1, self.recipient, selection)['feedback']['selection'], selection)

    def test_twenty_message_window_orders_timestamp_ties_and_marks_prior_media(self):
        settings = dict(self.pipeline['settings'], context_message_limit=20)
        for i in range(30):
            event = dict(self.target, message_id=f'old-{i}', kind='text', sticker=None,
                         text=f'old {i}', sent_at='2020-01-01T00:00:00+00:00')
            if i == 29:
                event.update(kind='image', text=None)
            self.store.observe(event, settings)
        self.store.observe(dict(self.target, reply_to_message_id='old-0'), settings)
        request = self.store.load_job(1)['request']
        self.assertEqual(request['context_message_limit'], 20)
        self.assertEqual([m['message_id'] for m in request['recent_messages']],
                         [f'old-{i}' for i in range(10, 30)])
        self.assertEqual(request['reply_to_message_id'], 'old-0')
        self.assertNotIn('old-0', [m['message_id'] for m in request['recent_messages']])
        media = request['recent_messages'][-1]
        self.assertTrue(media['media_not_interpreted'])
        self.assertIsNone(media['text'])
        self.assertIsNone(request['context_age_limit'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM messages').fetchone()[0], 31)

    def test_database_upgrade_adds_command_receipts_without_rewriting_old_results(self):
        self.process()
        before = self.store.load_job(1)
        self.store.save_feedback(1, self.recipient, 'first')
        with self.store.db:
            self.store.db.execute('DROP TABLE fetch_commands')
        self.restart()
        self.assertEqual(self.store.load_job(1), before)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM feedback').fetchone()[0], 1)
        tools = FetchTools(self.store)
        args = {'window_id': 1, 'selection': 'neither'}
        first = tools.call('save_feedback', args,
            authenticated_recipient_id=self.recipient, command_id='new-after-upgrade')
        self.restart()
        replay = FetchTools(self.store).call('save_feedback', args,
            authenticated_recipient_id=self.recipient, command_id='new-after-upgrade')
        self.assertEqual(first, replay)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM feedback').fetchone()[0], 2)
        self.assertEqual(len(self.model.calls), 1)
        self.assertEqual(len(self.transport.attempts), 1)

    def test_context_never_reads_another_platform_or_conversation(self):
        for platform, conversation, canary in (
            ('another-platform', self.target['conversation_id'], 'platform-secret'),
            (self.target['platform'], 'another-conversation', 'conversation-secret'),
        ):
            self.store.enroll(platform, conversation, self.recipient, 'separate-private-thread',
                              [self.recipient, self.target['sender_id']])
            foreign = dict(self.events[0], platform=platform, conversation_id=conversation, text=canary)
            self.store.observe(foreign, self.pipeline['settings'])
        self.prepare()
        request = self.store.load_job(1)['request']
        self.assertEqual([m['message_id'] for m in request['recent_messages']],
                         [event['message_id'] for event in self.events[:-1]])
        self.assertNotIn('platform-secret', json.dumps(request))
        self.assertNotIn('conversation-secret', json.dumps(request))

    def test_each_recipient_gets_only_their_declared_preferences_and_relationship(self):
        second = 'second-recipient'
        self.store.enroll(self.target['platform'], self.target['conversation_id'], second,
                         'second-private-thread', [second, self.target['sender_id']])
        self.store.set_preferences(self.target['platform'], second, 'es', 'detailed')
        self.store.set_relationship(self.target['platform'], second, self.target['sender_id'], 'friend')
        self.prepare()
        requests = [self.store.load_job(row['id'])['request']
                    for row in self.store.db.execute('SELECT id FROM context_windows').fetchall()]
        users = {request['recipient_id']: request['user_context'] for request in requests}
        self.assertEqual(users[self.recipient]['preferences'], {'language': 'en', 'explanation_length': 'short'})
        self.assertIsNone(users[self.recipient]['relationship'])
        self.assertEqual(users[second]['preferences'], {'language': 'es', 'explanation_length': 'detailed'})
        self.assertEqual(users[second]['relationship'], 'friend')
        self.assertEqual(users[second]['preferences_source'], 'user_declared')


if __name__ == '__main__':
    unittest.main()
