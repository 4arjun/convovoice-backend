from django.urls import path
from .views import ConversationListCreate

urlpatterns = [
    path('conversations/', ConversationListCreate.as_view(), name='conversation-list-create'),
]
