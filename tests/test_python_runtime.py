"""Core workflows must run without compiler or optional SDK packages installed."""
import json
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PythonRuntimeTests(unittest.TestCase):
    def test_standard_library_pipeline_policy_persistence_and_feedback(self):
        # An isolated child prevents installed packages or a previous importer from
        # hiding a dependency. Exercise real SQLite and policy, with fake I/O only.
        script = textwrap.dedent("""
            import importlib.abc
            import json
            from pathlib import Path
            import socket
            import sys
            import tempfile

            sys.path.insert(0, sys.argv[1])

            class NoOptionalPackages(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if fullname.split('.')[0] in {
                        'jaclang', 'llvmlite', 'openai', 'PIL', 'uagents', 'dotenv'
                    }:
                        raise AssertionError('Unexpected dependency: ' + fullname)

            sys.meta_path.insert(0, NoOptionalPackages())
            def deny_network(*args, **kwargs):
                raise AssertionError('Network forbidden')

            socket.socket = deny_network
            from src import assembly, context, contracts, delivery, fetch_tools
            from src import interpreter, main, repository, routing, store
            from src.context_store import SQLiteStore
            from src.t5_mocks import MockTransport, demo_events, fixture

            calls = []
            def vision(request):
                calls.append(request)
                return fixture('candidate_compatible')

            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'store.sqlite3'
                db = SQLiteStore(path)
                events = demo_events()
                target = events[-1]
                recipient = fixture('interpretation_request')['recipient_id']
                db.enroll(target['platform'], target['conversation_id'], recipient,
                          'private-thread', [recipient, target['sender_id']])
                transport = MockTransport()
                pipeline = main.create_pipeline(
                    db, lambda request: assembly.interpret_saved(request, vision), transport)
                for event in events:
                    outcome = main.process_event(pipeline, event, authenticated=True)
                assert outcome[0]['status'] == 'accepted'
                before = db.load_job(1)
                assert before['result']['candidate_relation'] == 'compatible'
                assert before['result']['alternative']
                feedback = db.save_feedback(1, recipient, 'second')
                assert feedback['feedback']['provenance'] == 'recipient_judgment'
                db.close()
                db = SQLiteStore(path)
                pipeline = main.create_pipeline(db, lambda _: None, transport)
                assert main.process_event(pipeline, target, authenticated=True)[0][
                    'status'] == 'already_accepted'
                assert db.load_job(1) == before
                assert len(calls) == len(transport.attempts) == 1
                try:
                    db.get_explanation(1, 'other-recipient')
                except PermissionError:
                    pass
                else:
                    raise AssertionError('Recipient scope was bypassed')
                db.close()
            print(json.dumps({'accepted': True, 'replay_sent': False}))
        """)
        result = subprocess.run(
            [sys.executable, '-I', '-S', '-c', script, str(ROOT)],
            cwd=ROOT, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'accepted': True, 'replay_sent': False})

    def test_mock_cli_runs_without_site_packages(self):
        result = subprocess.run(
            [sys.executable, '-S', '-m', 'src', 'mock-demo', '--case', 'opposing', '--replay'],
            cwd=ROOT, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertFalse(output['phone_delivery_verified'])
        self.assertEqual(output['model_calls_mocked'], 1)


if __name__ == '__main__':
    unittest.main()
