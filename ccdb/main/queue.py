import datetime as dt
import json
import logging
from decimal import Decimal

import pika
from django.conf import settings
from django_lifecycle import LifecycleModel, hook

ALLOWED_EXCHANGES = ("billing", "contracts")
LOGGER = logging.getLogger(__name__)


def get_queue_environment():
    if settings.GLOBALWAYS_QUEUE_ENV in ("gw", "gw-dev"):
        return settings.GLOBALWAYS_QUEUE_ENV
    return "gw-dev" if settings.DEBUG else "gw"


def get_exchange_name(exchange):
    if exchange not in ALLOWED_EXCHANGES:
        raise ValueError(
            f"Invalid exchange: {exchange}, must be one of {ALLOWED_EXCHANGES}"
        )
    env = get_queue_environment()
    if not exchange.startswith(env):
        exchange = f"{env}.{exchange}"
    return exchange


def send_queue(exchange: str, message_type: str, payload: dict, source: str = None):
    """
    exchange is the name of the exchange as defined in gq-spec:exchanges.json

    CCDB will typically publish to the gw.billing and gw.contracts exchanges, and
    will subscribe to the gw.customers exchange.
    """
    exchange = get_exchange_name(exchange)
    if not source:
        source = settings.GLOBALWAYS_QUEUE_SOURCE
    if not source.startswith(settings.GLOBALWAYS_QUEUE_SOURCE):
        source = f"{settings.GLOBALWAYS_QUEUE_SOURCE}.{source}"

    message = {
        "type": message_type,
        "source": source,
        "payload": payload,
    }
    if not settings.GLOBALWAYS_QUEUE_URL:
        LOGGER.warning("No queue URL defined, not sending message")
        LOGGER.debug("Message would have been: %s", json.dumps(payload))
        return

    properties = pika.BasicProperties(content_type="application/json")
    connection_params = pika.ConnectionParameters(settings.GLOBALWAYS_QUEUE_URL)
    connection = pika.BlockingConnection(connection_params)
    with connection.channel() as channel:
        channel.basic_publish(
            exchange=exchange,
            body=json.dumps(message),
            properties=properties,
            routing_key="",
        )


class QueueModelMixin(LifecycleModel):
    queue_exchange = None
    queue_source = None
    queue_message_type = None
    queue_create_type = "new"
    queue_update_type = "update"
    queue_delete_type = "delete"
    queue_id_field = "id"
    queue_fields = ()
    queue_field_aliases = {}

    @classmethod
    def _serialize_queue_field(cls, obj, field):
        subfield = None
        if "__" in field:
            field, subfield = field.split("__", maxsplit=1)
        try:
            value = getattr(obj, field)
        except Exception:
            return None
        if callable(value):
            value = value()
        if subfield:
            return cls._serialize_queue_field(value, subfield)
        if isinstance(value, (dt.date, dt.datetime)):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = float(value)
        return value

    def _serialize_queue_create(self):
        result = {}
        for field in self.queue_fields:
            result[field] = self._serialize_queue_field(self, field)
        for field, alias in self.queue_field_aliases.items():
            result[alias] = self._serialize_queue_field(self, field)
        return result

    def _serialize_queue_update(self):
        result = self._serialize_queue_delete()
        for field in self.queue_fields:
            if self.has_changed(field):
                result[field] = self._serialize_queue_field(self, field)
        for field, alias in self.queue_field_aliases.items():
            if "__" not in field and self.has_changed(field):
                result[alias] = self._serialize_queue_field(self, field)
        return result

    def _serialize_queue_delete(self):
        return {self.queue_id_field: getattr(self, self.queue_id_field)}

    def _send_queue(self, message_type, payload):
        from main.tasks import send_queue_task

        send_queue_task.apply_async(
            kwargs={
                "exchange": self.queue_exchange,
                "message_type": message_type,
                "payload": payload,
                "source": self.queue_source,
            }
        )

    @hook("after_create", on_commit=True)
    def send_queue_create(self, extra_payload=None):
        payload = self._serialize_queue_create()
        if extra_payload:
            payload.update(extra_payload)
        self._send_queue(f"{self.queue_message_type}.{self.queue_create_type}", payload)

    @hook("after_update", has_changed=True)
    def send_queue_update(self, extra_payload=None):
        payload = self._serialize_queue_update()
        if extra_payload:
            payload.update(extra_payload)
        if len(payload) == 1 and self.queue_id_field in payload:
            # Not sending an empty ID notification, at least one thing needs to have changed.
            return
        self._send_queue(f"{self.queue_message_type}.{self.queue_update_type}", payload)

    @hook("after_delete", on_commit=True)
    def send_queue_delete(self):
        self._send_queue(
            f"{self.queue_message_type}.{self.queue_delete_type}",
            self._serialize_queue_delete(),
        )

    class Meta:
        abstract = True
