"""Thin object port over Jac's durable context, policy and transaction functions."""
from . import repository, store


class SQLiteStore:
    def __init__(self, path):
        self.db = repository.connect(str(path))
        store.initialize(self.db)

    def close(self):
        self.db.close()

    def enroll(self, *args, **kwargs):
        return repository.enroll(self.db, *args, **kwargs)

    def set_preferences(self, *args, **kwargs):
        return repository.set_preferences(self.db, *args, **kwargs)

    def set_relationship(self, *args, **kwargs):
        return repository.set_relationship(self.db, *args, **kwargs)

    def observe(self, event, settings):
        return store.observe(self.db, event, settings)

    def load_job(self, window_id):
        return store.load_job(self.db, window_id)

    def resolve_route(self, window_id):
        return store.resolve_route(self.db, window_id)

    def resolve_delivery(self, platform, delivery):
        row = self.db.execute(
            'SELECT id FROM context_windows WHERE platform=? AND conversation_id=? '
            'AND source_message_id=? AND recipient_id=?',
            (platform, delivery['source_conversation_id'], delivery['source_message_id'], delivery['recipient_id']),
        ).fetchone()
        if row is None:
            raise PermissionError('Saved exchange unavailable.')
        return self.resolve_route(row['id'])

    def claim(self, window_id, phase):
        return store.claim(self.db, window_id, phase)

    def save_result(self, window_id, result):
        from .main import format_delivery, validate_result

        request = self.load_job(window_id)['request']
        result = validate_result(result, request['source_message_id'])
        return store.save_result(self.db, window_id, result, format_delivery(request, result)['text'])

    def mark_failure(self, window_id, state, error_code):
        return store.mark_failure(self.db, window_id, state, error_code)

    def mark_accepted(self, window_id, receipt):
        return store.mark_accepted(self.db, window_id, receipt)

    def get_explanation(self, window_id, authenticated_recipient_id):
        return store.get_explanation(self.db, window_id, authenticated_recipient_id)

    def save_feedback(self, window_id, authenticated_recipient_id, selection, note=None):
        return store.feedback(self.db, window_id, authenticated_recipient_id, selection, note)

    def resolve_window(self, source_id, authenticated_recipient_id):
        rows = self.db.execute(
            'SELECT id FROM context_windows WHERE source_message_id=? AND recipient_id=?',
            (source_id, authenticated_recipient_id),
        ).fetchall()
        if not authenticated_recipient_id or len(rows) != 1:
            raise PermissionError('Saved exchange unavailable.')
        return rows[0]['id']
