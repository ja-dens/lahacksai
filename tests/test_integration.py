"""T5 assembly against doubles. No assertion here establishes a live integration."""

import copy
import io
import json
import os
import socket
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from unittest.mock import patch

from src.main import create_pipeline, load_settings, process_event, request_digest, run_window
from src.t5_mocks import MockInterpreter, MockStore, MockTransport, demo_events, fixture


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        for name in ('socket', 'create_connection'):
            guard = patch.object(socket, name, side_effect=AssertionError('Network forbidden in T5 mock tests'))
            guard.start()
            self.addCleanup(guard.stop)
        self.store, self.model, self.transport = MockStore(), MockInterpreter(), MockTransport()
        self.pipeline = create_pipeline(self.store, self.model, self.transport)
        self.events = demo_events()
        self.target = self.events[-1]
        for event in self.events[:-1]:
            self.assertEqual(self.process(event)[0]['status'], 'history_only')

    def process(self, event=None):
        return process_event(self.pipeline, self.target if event is None else event, authenticated=True)

    def prepare(self):
        return self.store.observe(self.target, self.pipeline['settings'])[0]

    def change_snapshot(self, window_id, mutate):
        request = self.store.jobs[window_id]['request']
        mutate(request)
        self.store.jobs[window_id]['request_sha256'] = request_digest(request)

    def test_automatic_one_call_and_private_delivery_without_feedback(self):
        result = self.process()[0]
        self.assertEqual(result['status'], 'accepted')
        self.assertFalse(result['delivered'])
        self.assertFalse(result['phone_delivery_verified'])
        self.assertEqual(len(self.model.calls), 1)
        self.assertEqual(len(self.transport.attempts), 1)
        sent = self.transport.attempts[0]
        self.assertEqual(sent['delivery'], fixture('private_delivery'))
        self.assertEqual(sent['route']['destination'], 'demo-private-assistant-thread')
        self.assertNotEqual(sent['route']['destination'], sent['delivery']['source_conversation_id'])
        self.assertEqual(self.store.feedback, [])
        self.assertEqual(self.model.calls[0]['sticker'], self.target['sticker'])

    def test_replay_does_not_repeat_model_or_send(self):
        self.process()
        self.assertEqual(self.process()[0]['status'], 'already_accepted')
        self.assertEqual(len(self.model.calls), 1)
        self.assertEqual(len(self.transport.attempts), 1)
        self.assertEqual(len(self.store.jobs), 1)

    def test_distinct_messages_reusing_image_both_trigger(self):
        self.process()
        self.process(dict(self.target, message_id='another-sticker'))
        self.assertEqual(len(self.model.calls), 2)
        self.assertEqual(len(self.store.jobs), 2)
        self.assertEqual(len({a['idempotency_key'] for a in self.transport.attempts}), 2)
        self.assertEqual(self.model.calls[1]['recent_messages'][-1]['kind'], 'sticker')
        self.assertTrue(self.model.calls[1]['recent_messages'][-1]['media_not_interpreted'])

    def test_changed_content_under_same_source_id_is_rejected(self):
        self.process()
        with self.assertRaisesRegex(ValueError, 'different content'):
            self.process(dict(self.target, text='changed source body'))
        self.assertEqual(len(self.model.calls), 1)
        self.assertEqual(len(self.transport.attempts), 1)

    def test_untrusted_or_assistant_events_do_not_reach_store(self):
        before = copy.deepcopy(self.store.history)
        self.assertEqual(process_event(self.pipeline, self.target)[0]['status'], 'rejected_unauthenticated')
        event = dict(self.target, authenticated=True)
        self.assertEqual(process_event(self.pipeline, event)[0]['status'], 'rejected_unauthenticated')
        self.assertEqual(self.process(dict(self.target, from_assistant=True))[0]['status'], 'ignored_assistant')
        self.assertEqual(self.store.history, before)
        self.assertEqual(self.model.calls, [])
        self.assertEqual(self.transport.attempts, [])

    def test_paused_and_unenrolled_conversations_do_not_trigger(self):
        self.store.routes[0]['enabled'] = False
        self.assertEqual(self.process()[0]['status'], 'ignored_unenrolled_or_paused')
        self.store.routes.clear()
        self.assertEqual(self.process()[0]['status'], 'ignored_unenrolled_or_paused')
        self.assertEqual(self.model.calls, [])
        self.assertEqual(self.transport.attempts, [])

    def test_two_recipients_have_separate_jobs_requests_and_destinations(self):
        other = copy.deepcopy(self.store.routes[0])
        other.update(recipient_id='demo-second-recipient', destination='another-private-thread')
        other['members'].append(other['recipient_id'])
        self.store.routes.append(other)
        profile = copy.deepcopy(self.store.profiles[self.store.routes[0]['recipient_id']])
        profile['preferences'] = {'language': 'es', 'explanation_length': 'detailed'}
        profile['relationship'] = 'friend'
        self.store.profiles[other['recipient_id']] = profile
        self.assertEqual([r['status'] for r in self.process()], ['accepted', 'accepted'])
        self.assertEqual(len(self.model.calls), 2)
        self.assertEqual(self.model.calls[1]['user_context'], profile)
        self.assertNotEqual(self.model.calls[0]['recipient_id'], self.model.calls[1]['recipient_id'])
        self.assertEqual({a['route']['destination'] for a in self.transport.attempts},
                         {'another-private-thread', 'demo-private-assistant-thread'})

    def test_history_and_destination_are_scoped_by_conversation(self):
        other = copy.deepcopy(self.store.routes[0])
        other.update(conversation_id='demo-other-chat', destination='demo-other-private-thread')
        self.store.routes.append(other)
        self.process(dict(self.target, conversation_id=other['conversation_id']))
        self.assertEqual(self.model.calls[0]['recent_messages'], [])
        self.assertEqual(self.transport.attempts[0]['route']['destination'], other['destination'])

    def test_twenty_message_override_is_forwarded_and_bounded(self):
        settings = load_settings({'CONTEXT_MESSAGE_LIMIT': '20'})
        self.pipeline = create_pipeline(self.store, self.model, self.transport, settings)
        start = datetime.fromisoformat(self.target['sent_at']) - timedelta(minutes=10)
        for i in range(30):
            event = dict(self.events[0], message_id=f'prior-{i}', sent_at=(start + timedelta(seconds=i)).isoformat())
            self.process(event)
        self.process()
        request = self.model.calls[0]
        self.assertEqual(request['context_message_limit'], 20)
        self.assertEqual(len(request['recent_messages']), 20)
        self.assertEqual(len(self.store.history), 33)
        self.assertEqual(self.store.observed_settings[-1]['context_message_limit'], 20)

    def test_old_context_is_kept_without_age_cutoff(self):
        self.process(dict(self.events[0], message_id='old-context', sent_at='2020-01-01T00:00:00Z'))
        self.process()
        request = self.model.calls[0]
        self.assertIsNone(request['context_age_limit'])
        self.assertIn('old-context', [m['message_id'] for m in request['recent_messages']])

    def test_future_messages_are_excluded_even_if_already_observed(self):
        self.process(dict(self.events[0], message_id='future', sent_at='2070-01-01T00:00:00Z'))
        self.process()
        self.assertNotIn('future', [m['message_id'] for m in self.model.calls[0]['recent_messages']])

    def test_snapshot_is_frozen_before_new_messages_and_profile_changes(self):
        def later_activity(_request):
            self.process(dict(self.events[0], message_id='later-reply', sent_at='2070-01-01T00:00:00Z'))
            self.store.profiles['demo-older-recipient']['relationship'] = 'changed later'
        self.model.hook = later_activity
        self.process()
        request = self.model.calls[0]
        self.assertEqual(request['user_context']['relationship'], 'grandchild')
        self.assertNotIn('later-reply', [m['message_id'] for m in request['recent_messages']])
        self.assertEqual(self.store.jobs[1]['request'], request)
        self.assertEqual(self.store.jobs[1]['request_sha256'], request_digest(request))

    def test_long_text_is_marked_bounded_and_raw_history_remains(self):
        for i in range(8):
            self.process(dict(self.events[0], message_id=f'long-{i}', text='x' * 5000))
        self.process(dict(self.target, text='y' * 5000))
        request = self.model.calls[0]
        self.assertEqual(sum(len(m['text'] or '') for m in request['recent_messages']), 24000)
        self.assertTrue(any(m['text_truncated'] for m in request['recent_messages']))
        self.assertEqual(len(request['target_text']), 4000)
        self.assertTrue(request['target_text_truncated'])
        self.assertEqual(len(self.store.history[-1]['text']), 5000)

    def test_feedback_is_never_retrieved_into_live_request(self):
        self.store.feedback.append({'window_id': 999, 'selection': 'second', 'note': 'not a universal meaning'})
        self.process()
        self.assertEqual(set(self.model.calls[0]['user_context']),
                         {'preferences', 'preferences_source', 'relationship', 'relationship_source'})
        self.assertNotIn('feedback', self.model.calls[0])

    def test_tampered_snapshot_hash_blocks_all_calls(self):
        window_id = self.prepare()
        self.store.jobs[window_id]['request']['target_text'] = 'tampered'
        self.assertEqual(run_window(self.pipeline, window_id)['status'], 'blocked')
        self.assertEqual(self.model.calls, [])
        self.assertEqual(self.transport.attempts, [])

    def test_invalid_context_or_feedback_input_is_blocked(self):
        changes = [
            lambda r: r.update(context_age_limit=3600),
            lambda r: r.update(context_message_limit=19),
            lambda r: r.update(feedback=['unapproved memory']),
            lambda r: r['user_context'].update(feedback=['unapproved memory']),
            lambda r: r['recent_messages'][0].update(sent_at='2070-01-01T00:00:00Z'),
            lambda r: r['recent_messages'][0].update(text='x' * 4001),
        ]
        for change in changes:
            with self.subTest(change=change):
                store, model, transport = MockStore(), MockInterpreter(), MockTransport()
                pipeline = create_pipeline(store, model, transport)
                for event in self.events[:-1]:
                    process_event(pipeline, event, authenticated=True)
                window_id = store.observe(self.target, pipeline['settings'])[0]
                change(store.jobs[window_id]['request'])
                store.jobs[window_id]['request_sha256'] = request_digest(store.jobs[window_id]['request'])
                self.assertEqual(run_window(pipeline, window_id)['status'], 'blocked')
                self.assertEqual(model.calls, [])
                self.assertEqual(transport.attempts, [])

    def test_compatible_opposing_and_unsupported_results_use_agreed_policy(self):
        for name in ('result_compatible', 'result_opposing', 'result_unsupported'):
            with self.subTest(case=name):
                self.model.result_name = name
                target = dict(self.target, message_id=name)
                self.assertEqual(self.process(target)[0]['status'], 'accepted')
                delivered_text = self.transport.attempts[-1]['delivery']['text']
                result = fixture(name)
                if name == 'result_compatible':
                    self.assertIn(result['alternative'], delivered_text)
                elif name == 'result_opposing':
                    self.assertIn(result['meaning'], delivered_text)
                    self.assertIn(result['uncertainty_caveat'], delivered_text)
                    self.assertNotIn(fixture('candidate_opposing')['candidates'][1], delivered_text)
                else:
                    self.assertIn('cannot reliably interpret', delivered_text)

    def test_bad_model_output_cannot_select_recipient_or_show_opposing_pair(self):
        for malformed in ('routing', 'opposing', 'wrong-source', 'invalid-json'):
            with self.subTest(malformed=malformed):
                store, transport = MockStore(), MockTransport()
                result = fixture('result_opposing')
                if malformed == 'routing':
                    result['recipient_id'] = 'attacker'
                elif malformed == 'opposing':
                    result['alternative'] = 'directly opposite meaning'
                elif malformed == 'wrong-source':
                    result['source_message_id'] = 'other-target'
                else:
                    result = 'invalid JSON'
                pipeline = create_pipeline(store, lambda _: result, transport)
                outcome = process_event(pipeline, self.target, authenticated=True)[0]
                self.assertEqual(outcome['status'], 'interpretation_failed')
                self.assertEqual(transport.attempts, [])

    def test_unsupported_media_abstains_without_model_call(self):
        for media in (None, dict(self.target['sticker'], mime_type='image/gif'),
                      dict(self.target['sticker'], data_base64='bad base64')):
            with self.subTest(media=bool(media)):
                self.process(dict(self.target, message_id=f'unsupported-{len(self.store.jobs)}', sticker=media))
        self.assertEqual(self.model.calls, [])
        self.assertEqual(len(self.transport.attempts), 3)
        self.assertTrue(all('cannot reliably interpret' in a['delivery']['text'] for a in self.transport.attempts))

    def test_model_failure_requires_explicit_retry_of_original_snapshot(self):
        self.model.failures_remaining = 1
        self.assertEqual(self.process()[0]['status'], 'interpretation_failed')
        frozen = copy.deepcopy(self.store.jobs[1]['request'])
        self.assertEqual(self.process()[0]['status'], 'retry_required')
        self.process(dict(self.events[0], message_id='later-context'))
        self.store.profiles['demo-older-recipient']['relationship'] = 'changed'
        self.assertEqual(run_window(self.pipeline, 1, retry=True)['status'], 'accepted')
        self.assertEqual(self.model.calls, [frozen, frozen])
        self.assertEqual(len(self.transport.attempts), 1)

    def test_definitive_send_rejection_retry_reuses_result_and_key(self):
        self.transport.rejections_remaining = 1
        self.assertEqual(self.process()[0]['status'], 'send_failed')
        self.assertEqual(self.process()[0]['status'], 'retry_required')
        self.assertEqual(run_window(self.pipeline, 1, retry=True)['status'], 'accepted')
        self.assertEqual(len(self.model.calls), 1)
        self.assertEqual(len(self.transport.attempts), 2)
        self.assertEqual(self.transport.attempts[0], self.transport.attempts[1])

    def test_lost_send_acknowledgment_requires_reconciliation_not_resend(self):
        self.transport.timeout_after_accept = True
        self.assertEqual(self.process()[0]['status'], 'reconciliation_required')
        self.assertEqual(len(self.transport.receipts), 1)
        self.assertEqual(self.process()[0]['status'], 'reconciliation_required')
        self.assertEqual(run_window(self.pipeline, 1, retry=True)['status'], 'reconciliation_required')
        self.assertEqual(len(self.transport.attempts), 1)
        self.assertEqual(len(self.model.calls), 1)

    def test_invalid_acknowledgment_is_not_recorded_as_acceptance(self):
        self.transport.send_private = lambda *_: {'status': 'accepted'}
        self.assertEqual(self.process()[0]['status'], 'reconciliation_required')
        self.assertEqual(self.store.jobs[1]['state'], 'delivery_unknown')
        self.assertIsNone(self.store.jobs[1]['receipt'])

    def test_raw_transport_details_are_not_persisted_or_claimed_as_phone_receipt(self):
        self.transport.send_private = lambda *_: {'status': 'accepted', 'provider_message_id': 'mock-1',
                                                  'delivered': True, 'private_debug': 'discard this detail'}
        result = self.process()[0]
        self.assertFalse(result['delivered'])
        self.assertFalse(result['phone_delivery_verified'])
        self.assertEqual(self.store.jobs[1]['receipt'], {'status': 'accepted', 'provider_message_id': 'mock-1'})

    def test_inconsistent_final_interpretation_shapes_are_rejected(self):
        for updates in ({'status': 'interpreted', 'candidate_relation': 'compatible'},
                        {'status': 'ambiguous', 'candidate_relation': 'single'},
                        {'status': 'ambiguous', 'candidate_relation': 'compatible', 'alternative': None},
                        {'status': 'ambiguous', 'candidate_relation': 'compatible',
                         'alternative': fixture('interpretation_result')['meaning']}):
            with self.subTest(updates=updates):
                store, transport = MockStore(), MockTransport()
                result = dict(fixture('interpretation_result'), **updates)
                pipeline = create_pipeline(store, lambda _: result, transport)
                outcome = process_event(pipeline, self.target, authenticated=True)[0]
                self.assertEqual(outcome['status'], 'interpretation_failed')
                self.assertEqual(transport.attempts, [])

    def test_crash_after_provider_acceptance_does_not_resend_on_restart(self):
        with patch.object(self.store, 'mark_accepted', side_effect=KeyboardInterrupt('synthetic crash')):
            with self.assertRaises(KeyboardInterrupt):
                self.process()
        self.assertEqual(self.store.jobs[1]['state'], 'sending')
        # Same retained fake store, new coordinator. This is NOT disk/process recovery.
        self.pipeline = create_pipeline(self.store, self.model, self.transport)
        self.assertEqual(self.process()[0]['status'], 'reconciliation_required')
        self.assertEqual(len(self.transport.attempts), 1)

    def test_crash_after_model_call_does_not_silently_repeat_possible_billing(self):
        with patch.object(self.store, 'save_result', side_effect=KeyboardInterrupt('synthetic crash')):
            with self.assertRaises(KeyboardInterrupt):
                self.process()
        self.assertEqual(self.store.jobs[1]['state'], 'interpreting')
        self.pipeline = create_pipeline(self.store, self.model, self.transport)
        self.assertEqual(self.process()[0]['status'], 'reconciliation_required')
        self.assertEqual(run_window(self.pipeline, 1, retry=True)['status'], 'reconciliation_required')
        self.assertEqual(len(self.model.calls), 1)
        self.assertEqual(self.transport.attempts, [])

    def test_invalid_internal_job_identity_or_state_cannot_trigger_work(self):
        window_id = self.prepare()
        original = copy.deepcopy(self.store.jobs[window_id])
        for mutation in ({'window_id': 999}, {'state': 'unrecognized-state'}):
            with self.subTest(mutation=mutation):
                self.store.jobs[window_id] = dict(original, **mutation)
                self.assertEqual(run_window(self.pipeline, window_id)['status'], 'blocked')
        self.assertEqual(self.model.calls, [])
        self.assertEqual(self.transport.attempts, [])

    def test_failed_atomic_claim_does_not_trigger_interpretation(self):
        window_id = self.prepare()
        with patch.object(self.store, 'claim', return_value=False):
            self.assertEqual(run_window(self.pipeline, window_id)['status'], 'busy')
        self.assertEqual(self.model.calls, [])
        self.assertEqual(self.transport.attempts, [])

    def test_reentrant_event_cannot_make_a_second_model_call(self):
        nested = []
        self.model.hook = lambda _: nested.append(self.process()[0]['status'])
        self.assertEqual(self.process()[0]['status'], 'accepted')
        self.assertEqual(nested, ['reconciliation_required'])
        self.assertEqual(len(self.model.calls), 1)

    def test_revoked_enrollment_after_model_prevents_send(self):
        self.model.hook = lambda _: self.store.routes[0].update(enabled=False)
        self.assertEqual(self.process()[0]['status'], 'blocked')
        self.assertEqual(self.transport.attempts, [])
        self.model.hook = None
        self.store.routes[0]['enabled'] = True
        self.assertEqual(run_window(self.pipeline, 1, retry=True)['status'], 'accepted')
        self.assertEqual(len(self.model.calls), 1)

    def test_wrong_membership_identity_or_group_destination_is_blocked(self):
        for mutation in (
            {'recipient_id': 'different-recipient'}, {'platform': 'other-platform'},
            {'conversation_id': 'other-chat'}, {'members': []},
            {'destination': self.target['conversation_id']}, {'enabled': False},
        ):
            with self.subTest(mutation=mutation):
                window_id = self.prepare()
                route = dict(self.store.routes[0], **mutation)
                with patch.object(self.store, 'resolve_route', return_value=route):
                    self.assertEqual(run_window(self.pipeline, window_id, retry=True)['status'], 'blocked')
        self.assertEqual(self.model.calls, [])
        self.assertEqual(self.transport.attempts, [])

    def test_model_mutating_its_input_cannot_change_saved_identity_or_route(self):
        self.model.hook = lambda request: request.update(recipient_id='model-chosen-recipient')
        self.assertEqual(self.process()[0]['status'], 'accepted')
        self.assertEqual(self.store.jobs[1]['request']['recipient_id'], 'demo-older-recipient')
        self.assertEqual(self.transport.attempts[0]['delivery']['recipient_id'], 'demo-older-recipient')

    def test_safe_error_category_excludes_exception_details(self):
        def fail(_request):
            raise RuntimeError('SYNTHETIC_PRIVATE_DETAIL do not persist')
        self.pipeline = create_pipeline(self.store, fail, self.transport)
        self.process()
        self.assertEqual(self.store.jobs[1]['errors'], ['RuntimeError'])
        self.assertNotIn('SYNTHETIC_PRIVATE_DETAIL', json.dumps(self.store.jobs))

    def test_configuration_rejects_invalid_window_and_live_memory(self):
        for value in ('8', '19', '26', 'nope'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                load_settings({'CONTEXT_MESSAGE_LIMIT': value})
        settings = load_settings()
        settings['feedback_live_retrieval_enabled'] = True
        with self.assertRaises(ValueError):
            create_pipeline(self.store, self.model, self.transport, settings)
        self.assertEqual(load_settings({'CONTEXT_MESSAGE_LIMIT': '25'})['context_message_limit'], 25)

    def test_cli_offline_demo_reports_mocks_and_no_real_delivery(self):
        from src.__main__ import main
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch('sys.argv', ['src', 'mock-demo', '--replay']), redirect_stdout(output):
            main()
        result = json.loads(output.getvalue())
        self.assertTrue(result['all_components_are_mocks'])
        self.assertFalse(result['phone_delivery_verified'])
        self.assertFalse(result['durable_store_implemented'])
        self.assertEqual(result['network_calls'], 0)
        self.assertEqual(result['model_calls_mocked'], 1)
        self.assertEqual(result['private_send_attempts_mocked'], 1)
        self.assertEqual(result['outcomes'][-1][0]['status'], 'already_accepted')


if __name__ == '__main__':
    unittest.main()
