from django.urls import path

from . import views

app_name = "cazari"

urlpatterns = [
    path("", views.AccommodationListView.as_view(), name="list"),
    path("adauga/", views.AccommodationCreateView.as_view(), name="create"),
    path("<int:pk>/editeaza/", views.AccommodationUpdateView.as_view(), name="update"),
    path("<int:pk>/sterge/", views.AccommodationDeleteView.as_view(), name="delete"),
]
