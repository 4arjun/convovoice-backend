import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from speechanalyser.consumers import AudioConsumer  # Ensure the correct import

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'convovoice.settings')

# Get the ASGI application
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/audio/", AudioConsumer.as_asgi()),  # Ensure this matches your consumer and URL pattern
        ])
    ),
})
