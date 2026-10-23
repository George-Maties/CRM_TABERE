from django.urls import path

from .views import WallView

app_name = "wall"

urlpatterns = [
    path("", WallView.as_view(), name="index"),
]
