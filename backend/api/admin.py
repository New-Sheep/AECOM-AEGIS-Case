from django.contrib import admin

from api.models import (
    Asset,
    AuditLog,
    Dependency,
    ShadowLog,
    Telemetry,
    WeatherContext,
)

admin.site.register(Asset)
admin.site.register(Telemetry)
admin.site.register(WeatherContext)
admin.site.register(Dependency)
admin.site.register(AuditLog)
admin.site.register(ShadowLog)
