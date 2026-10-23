from django.urls import path

from . import views

app_name = "oportunitati"

urlpatterns = [
    path("", views.OpportunityListView.as_view(), name="list"),
    path("adauga/", views.OpportunityCreateView.as_view(), name="create"),
    path("<int:pk>/", views.OpportunityDetailView.as_view(), name="detail"),
    path("<int:pk>/editeaza/", views.OpportunityUpdateView.as_view(), name="update"),
    path("<int:pk>/sterge/", views.OpportunityDeleteView.as_view(), name="delete"),
    path("<int:pk>/status/", views.StatusUpdateView.as_view(), name="status"),
    path("<int:pk>/note/", views.NoteCreateView.as_view(), name="note"),
]
