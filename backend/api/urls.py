from django.urls import path

from api.views import (
    ActionBriefView,
    AgentResumeView,
    AgentRunView,
    AssistantChatView,
    BriefView,
    ControlShutdownView,
    DashboardHeaderView,
    ForecastView,
    HealthView,
    ImpactView,
    PredictView,
    RiskMapView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("assets/risk_map/", RiskMapView.as_view(), name="risk_map"),
    path(
        "assets/<str:asset_id>/action_brief/",
        ActionBriefView.as_view(),
        name="action_brief",
    ),
    path(
        "assets/<str:asset_id>/forecast/",
        ForecastView.as_view(),
        name="forecast",
    ),
    path("dashboard/header/", DashboardHeaderView.as_view(), name="dashboard_header"),
    path("control/shutdown/", ControlShutdownView.as_view(), name="control_shutdown"),
    path("assistant/chat/", AssistantChatView.as_view(), name="assistant_chat"),
    # Nervous system (whiteboard)
    path("predict/", PredictView.as_view(), name="predict"),
    path("impact/<str:node_id>/", ImpactView.as_view(), name="impact"),
    path("brief/", BriefView.as_view(), name="brief"),
    # LangGraph agent
    path("agent/run/", AgentRunView.as_view(), name="agent_run"),
    path("agent/resume/", AgentResumeView.as_view(), name="agent_resume"),
]
