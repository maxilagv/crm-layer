from django.contrib import admin

from .models import (
    AIBehaviorPolicy,
    BusinessProfile,
    NotificationPolicy,
    SalesPolicy,
    SupportPolicy,
    WhatsAppPolicy,
)

for model in (
    BusinessProfile,
    SalesPolicy,
    SupportPolicy,
    AIBehaviorPolicy,
    NotificationPolicy,
    WhatsAppPolicy,
):
    admin.site.register(model)
