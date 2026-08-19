from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from core.games.api.views import EpisodeViewSet
from core.users.api.views import LoginView
from core.users.api.views import LogoutView

router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register("episodes", EpisodeViewSet, basename="episode")


app_name = "api"
urlpatterns = router.urls
urlpatterns += [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
]
