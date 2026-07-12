from django.db import models
from django.utils import timezone

class Customer(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    last_service_viewed_at = models.DateTimeField(null=True, blank=True)
    current_page = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.phone_number

class Message(models.Model):
    DIRECTION_CHOICES = (
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='messages')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    content = models.TextField() # Can be JSON string or simple text
    message_type = models.CharField(max_length=50, default='text') # text, interactive, template
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.direction} - {self.customer.phone_number}"
