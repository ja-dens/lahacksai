"""SDK/object glue; interpretation, routing and receipt policy remain in Jac."""
from dataclasses import asdict

from ..assembly import check_route, interpret_saved, receipt_policy
from ..main import process_event
from .photon import PhotonAdapter


class Interpreter:
    def __init__(self, vision):
        self.vision = vision
        self.metadata = dict(getattr(vision, 'metadata', {}))

    def __call__(self, request):
        return interpret_saved(request, self.vision)


class PhotonTransport:
    def __init__(self, store, *, project_id, platform, assistant_ids, client,
                 verify_event, decode_event, resolve_private, classify_attachment=None):
        if not callable(resolve_private):
            raise ValueError('A verified private-destination resolver is required')
        self.store, self.platform = store, platform
        self.resolve_private = resolve_private
        self.adapter = PhotonAdapter(
            project_id=project_id, platform=platform, assistant_ids=assistant_ids,
            client=client, verify_event=verify_event, decode_event=decode_event,
            resolve_destination=self._destination, classify_attachment=classify_attachment,
        )

    def _destination(self, delivery):
        route = self.store.resolve_delivery(self.platform, delivery)
        if not route['enabled']:
            raise PermissionError('Enrollment revoked')
        check_route(delivery, route, route)
        destination = self.resolve_private(delivery, route)
        if destination.space_id != route['destination']:
            raise PermissionError('Private destination does not match enrollment')
        return destination

    def send_private(self, delivery, route, idempotency_key):
        current = self.store.resolve_delivery(self.platform, delivery)
        try:
            check_route(delivery, route, current)
        except PermissionError:
            return {'status': 'rejected'}
        receipt = self.adapter.send_private_explanation(delivery)
        result = receipt_policy(asdict(receipt))
        result['idempotency_key'] = idempotency_key
        return result

    def receive_webhook(self, raw_body, headers, pipeline):
        # The callback is reachable only after T2 validates the exact raw bytes.
        return self.adapter.receive_webhook(
            raw_body, headers,
            lambda event: process_event(pipeline, event, authenticated=True),
        )
