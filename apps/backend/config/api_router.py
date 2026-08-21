from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from core.games.api.views import EpisodeViewSet
from core.qa.api.views import PropositionViewSet
from core.qa.api.views import QuestionImportView
from core.qa.api.views import QuestionViewSet
from core.users.api.views import LoginView
from core.users.api.views import LogoutView

router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register("episodes", EpisodeViewSet, basename="episode")
router.register("qa/questions", QuestionViewSet, basename="qa-question")
router.register("qa/propositions", PropositionViewSet, basename="qa-proposition")


app_name = "api"
urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path(
        "qa/questions/import/",
        QuestionImportView.as_view(),
        name="qa-question-import",
    ),
]
urlpatterns += router.urls
