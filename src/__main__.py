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
    from dotenv import load_dotenv
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['demo', 'inspect', 'doctor', 'live'])
    parser.add_argument('--db', default='local-data/demo.sqlite3')
    parser.add_argument('--window-id', type=int, default=1)
    parser.add_argument('--case', choices=['single', 'compatible', 'opposing', 'unsupported'], default='single')
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--direct', action='store_true')
    parser.add_argument('--once', action='store_true',
                        help='Poll Photon once and exit (live only)')
    parser.add_argument('--local', action='store_true',
                        help='Serve the offline demo as a page on this machine')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    if args.command == 'doctor':
        from .live import LiveConfig
        try:
            LiveConfig.from_env()
            photon_configuration = 'ready'
        except ValueError:
            photon_configuration = 'incomplete'
        result = {
            'api_key_configured': bool(os.getenv('OPENAI_API_KEY') or os.getenv('VISION_API_KEY')),
            'model_configured': bool(os.getenv('VISION_MODEL')),
            'photon_key_configured': bool(os.getenv('PHOTON_API_KEY')),
            'photon_configuration': photon_configuration,
            'live_ingress_verified': False, 'phone_delivery_verified': False,
        }
    elif args.command == 'live':
        from .live import run_live
        result = run_live(once=args.once)
    elif args.command == 'demo' and args.local:
        from .local_demo import serve
        serve(args.port)
        return
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
    if result is not None:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
