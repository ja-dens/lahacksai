"""Run only the T5 synthetic integration harness; no live mode is implemented."""

import argparse
import json
import os

from .main import create_pipeline, load_settings, process_event, run_window
from .t5_mocks import MockInterpreter, MockStore, MockTransport, demo_events


def main():
    parser = argparse.ArgumentParser(description='T5 offline mock integration')
    parser.add_argument('command', choices=['mock-demo'])
    parser.add_argument('--case', choices=['single', 'compatible', 'opposing', 'unsupported'], default='single')
    parser.add_argument('--replay', action='store_true', help='Replay the same target event')
    parser.add_argument('--fail', choices=['model', 'send-rejected', 'send-unknown'])
    parser.add_argument('--retry', action='store_true', help='Explicitly retry window 1 in this mock session')
    args = parser.parse_args()
    settings = load_settings(dict(os.environ))
    names = {'single': 'interpretation_result', 'compatible': 'result_compatible',
             'opposing': 'result_opposing', 'unsupported': 'result_unsupported'}
    store, interpreter, transport = MockStore(), MockInterpreter(names[args.case]), MockTransport()
    interpreter.failures_remaining = int(args.fail == 'model')
    transport.rejections_remaining = int(args.fail == 'send-rejected')
    transport.timeout_after_accept = args.fail == 'send-unknown'
    pipeline = create_pipeline(store, interpreter, transport, settings)
    events = demo_events()
    outcomes = [process_event(pipeline, event, authenticated=True) for event in events]
    if args.replay:
        outcomes.append(process_event(pipeline, events[-1], authenticated=True))
    if args.retry:
        outcomes.append([run_window(pipeline, 1, retry=True)])
    deliveries = [a['delivery'] for a in transport.attempts]
    print(json.dumps({
        'mode': 'mock', 'all_components_are_mocks': True, 'network_calls': 0,
        'phone_delivery_verified': False, 'durable_store_implemented': False,
        'model_calls_mocked': len(interpreter.calls), 'private_send_attempts_mocked': len(transport.attempts),
        'outcomes': outcomes, 'deliveries': deliveries,
        'windows': [{'window_id': j['window_id'], 'state': j['state'],
                     'request_sha256': j['request_sha256'], 'errors': j['errors']} for j in store.jobs.values()],
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
