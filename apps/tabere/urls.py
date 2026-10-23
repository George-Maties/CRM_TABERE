from django.urls import path

from . import rooms, views

app_name = "tabere"

urlpatterns = [
    path("", views.CampListView.as_view(), name="list"),
    path("adauga/", views.CampCreateView.as_view(), name="create"),
    path("<int:pk>/", views.CampDetailView.as_view(), name="detail"),
    path("<int:pk>/editeaza/", views.CampUpdateView.as_view(), name="update"),
    path("<int:pk>/sterge/", views.CampDeleteView.as_view(), name="delete"),
    path("<int:pk>/sarcini/", views.TaskCreateView.as_view(), name="task"),
    path("sarcini/<int:pk>/gata/", views.TaskToggleView.as_view(), name="task-toggle"),
    path("participanti/<int:pk>/copii/", views.ChildCreateView.as_view(), name="child-add"),
    path(
        "participanti/<int:pk>/merge/", views.ParticipantGoesView.as_view(), name="participant-goes"
    ),
    path("copii/<int:pk>/sterge/", views.ChildDeleteView.as_view(), name="child-delete"),
    path("<int:pk>/configurator/", rooms.ConfiguratorView.as_view(), name="configurator"),
    path("<int:pk>/camere/", rooms.RoomBatchCreateView.as_view(), name="rooms-add"),
    path("<int:pk>/camere/muta/", rooms.OccupantMoveView.as_view(), name="occupant-move"),
    path("<int:pk>/camere/excel/", rooms.RoomsExcelView.as_view(), name="rooms-excel"),
    path("camere/<int:pk>/sterge/", rooms.RoomDeleteView.as_view(), name="room-delete"),
]
