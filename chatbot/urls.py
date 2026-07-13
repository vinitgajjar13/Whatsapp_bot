from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.whatsapp_webhook, name='whatsapp_webhook'),
    path('api/all-data/', views.get_all_data, name='get_all_data'),
]
