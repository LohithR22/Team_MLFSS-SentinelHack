import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sentinel.settings')

# NOTE: get_asgi_application() must run before any ORM / consumer imports
# so Django apps finish initializing.
_django_asgi = get_asgi_application()

from core.consumers import AlertConsumer  # noqa: E402

application = ProtocolTypeRouter({
    'http': _django_asgi,
    'websocket': URLRouter([
        path('ws/alerts/', AlertConsumer.as_asgi()),
    ]),
})
