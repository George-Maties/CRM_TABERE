from django.urls import path

from .views import WelcomeView

app_name = "oportunitati"

urlpatterns = [
    path("", WelcomeView.as_view(), name="welcome"),
]
