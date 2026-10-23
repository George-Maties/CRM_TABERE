from django.urls import path

from .views import WelcomeView

app_name = "wall"

urlpatterns = [
    path("", WelcomeView.as_view(), name="welcome"),
]
