"""Offline application demo, preserved mock harness and local inspection."""
import argparse
import json
import os
import sys


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == 'mock-demo':
        from .mock_cli import main as mock_main
        return mock_main(argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['demo', 'inspect', 'doctor'])
    parser.add_argument('--db', default='local-data/demo.sqlite3')
    parser.add_argument('--window-id', type=int, default=1)
    parser.add_argument('--case', choices=['single', 'compatible', 'opposing', 'unsupported'], default='single')
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--direct', action='store_true')
    args = parser.parse_args(argv)
    if args.command == 'doctor':
        result = {
            'api_key_configured': bool(os.getenv('OPENAI_API_KEY') or os.getenv('VISION_API_KEY')),
            'model_configured': bool(os.getenv('VISION_MODEL')),
            'photon_key_configured': bool(os.getenv('PHOTON_API_KEY')),
            'live_ingress_verified': False, 'phone_delivery_verified': False,
        }
    elif args.command == 'demo':
        from .demo import run_demo
        result = run_demo(args.db, args.case, args.replay, args.direct)
    else:
        from .context_store import SQLiteStore
        store = SQLiteStore(args.db)
        try:
            result = store.load_job(args.window_id)
            if result['request'].get('sticker'):
                result['request']['sticker'].pop('data_base64', None)
        finally:
            store.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
