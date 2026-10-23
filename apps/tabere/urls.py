from django.urls import path

from . import views

app_name = "tabere"

urlpatterns = [
    path("", views.CampListView.as_view(), name="list"),
    path("adauga/", views.CampCreateView.as_view(), name="create"),
    path("<int:pk>/", views.CampDetailView.as_view(), name="detail"),
    path("<int:pk>/editeaza/", views.CampUpdateView.as_view(), name="update"),
    path("<int:pk>/sterge/", views.CampDeleteView.as_view(), name="delete"),
    path("<int:pk>/sarcini/", views.TaskCreateView.as_view(), name="task"),
    path("sarcini/<int:pk>/gata/", views.TaskToggleView.as_view(), name="task-toggle"),
]
