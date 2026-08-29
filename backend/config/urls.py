from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def root(_request):
    return JsonResponse(
        {
            "service": "AEGIS API",
            "sprint": 4,
            "hint": "Open Streamlit UI separately; this process is API-only.",
            "endpoints": {
                "health": "/api/v1/health/",
                "risk_map": "/api/v1/assets/risk_map/",
                "header": "/api/v1/dashboard/header/",
                "action_brief": "/api/v1/assets/<id>/action_brief/",
                "forecast": "/api/v1/assets/<id>/forecast/",
                "shutdown": "POST /api/v1/control/shutdown/",
                "predict": "POST /api/v1/predict/",
                "impact": "/api/v1/impact/<node_id>/",
                "brief": "POST /api/v1/brief/",
                "agent_run": "POST /api/v1/agent/run/",
                "agent_resume": "POST /api/v1/agent/resume/",
                "admin": "/admin/",
            },
            "ui": "streamlit run frontend/dashboard.py (from repo root)",
        }
    )


urlpatterns = [
    path("", root, name="root"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("api.urls")),
]
