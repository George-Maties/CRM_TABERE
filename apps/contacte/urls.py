from django.urls import path

from . import views

app_name = "contacte"

urlpatterns = [
    path("", views.ContactListView.as_view(), name="list"),
    path("adauga/", views.ContactCreateView.as_view(), name="create"),
    path("<int:pk>/", views.ContactDetailView.as_view(), name="detail"),
    path("<int:pk>/editeaza/", views.ContactUpdateView.as_view(), name="update"),
    path("<int:pk>/sterge/", views.ContactDeleteView.as_view(), name="delete"),
]
