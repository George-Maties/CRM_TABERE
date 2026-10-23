"""The room configurator of a camp: rooms of the accommodation, and who sleeps in each.

Who can be placed: the children of the camp's participants, and the parents or teachers
ticked "Merge în tabără". Each one is a key: "copil-<child id>" or "adult-<opportunity id>".
"""

from io import BytesIO

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import slugify
from django.views import View
from django.views.generic import DetailView
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.core.templatetags.ui import plural
from apps.oportunitati.models import Status

from .forms import RoomBatchForm
from .models import Camp, Child, Room


class Occupant:
    """A child, or a parent / teacher who comes along, as the configurator shows them."""

    def __init__(self, key, name, details, family, room_id, adult=False, child=None):
        self.key, self.name, self.details, self.family = key, name, details, family
        self.room_id, self.adult, self.child = room_id, adult, child


def participants_of(camp):
    """The camp's won opportunities, each with `occupants`: the contact first (if they come),
    then their children."""
    participants = list(
        camp.opportunities.filter(status=Status.WON)
        .select_related("contact")
        .prefetch_related("children")
        .order_by("contact__name")
    )
    for opportunity in participants:
        contact = opportunity.contact
        opportunity.occupants = []
        if opportunity.contact_goes:
            opportunity.occupants.append(
                Occupant(
                    f"adult-{opportunity.pk}",
                    contact.name,
                    contact.get_kind_display(),
                    contact.name,
                    opportunity.contact_room_id,
                    adult=True,
                )
            )
        for child in opportunity.children.all():
            details = " · ".join(
                part
                for part in (plural(child.age, "an,ani") if child.age else "", child.city)
                if part
            )
            opportunity.occupants.append(
                Occupant(
                    f"copil-{child.pk}",
                    child.name,
                    details,
                    contact.name,
                    child.room_id,
                    child=child,
                )
            )
    return participants


def rooms_with_occupants(camp, participants):
    rooms = list(camp.rooms.all())
    by_room = {room.pk: [] for room in rooms}
    names = {room.pk: room.name for room in rooms}
    for opportunity in participants:
        for occupant in opportunity.occupants:
            occupant.room_name = names.get(occupant.room_id, "")
            if occupant.room_id in by_room:
                by_room[occupant.room_id].append(occupant)
    for room in rooms:
        room.occupants = by_room[room.pk]
        room.free = max(room.capacity - len(room.occupants), 0)
        room.free_slots = range(room.free)
    return rooms


class ConfiguratorView(PermissionRequiredMixin, DetailView):
    permission_required = "tabere.change_room"
    model = Camp
    template_name = "tabere/configurator.html"

    def get_context_data(self, **kwargs):
        participants = participants_of(self.object)
        rooms = rooms_with_occupants(self.object, participants)
        occupants = [o for p in participants for o in p.occupants]
        context = {
            "participants": participants,
            "rooms": rooms,
            "room_form": kwargs.pop("room_form", None) or RoomBatchForm(),
            "people_count": len(occupants),
            "placed_count": sum(1 for o in occupants if o.room_id),
            "bed_count": sum(room.capacity for room in rooms),
        }
        context.update(kwargs)
        return super().get_context_data(**context)


class RoomBatchCreateView(PermissionRequiredMixin, View):
    permission_required = "tabere.add_room"
    http_method_names = ["post"]

    def post(self, request, pk):
        camp = get_object_or_404(Camp, pk=pk)
        form = RoomBatchForm(request.POST)
        if not form.is_valid():
            page = ConfiguratorView(request=request, kwargs={"pk": pk})
            page.object = camp
            return page.render_to_response(page.get_context_data(room_form=form))
        rooms = form.save(camp)
        messages.success(request, f"Am adăugat {plural(len(rooms), 'cameră,camere')}.")
        return redirect("tabere:configurator", pk=camp.pk)


class RoomDeleteView(PermissionRequiredMixin, View):
    permission_required = "tabere.delete_room"
    http_method_names = ["post"]

    def post(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        room.delete()
        messages.success(
            request, f"{room.name} a fost ștearsă; cine era în ea e din nou fără cameră."
        )
        return redirect("tabere:configurator", pk=room.camp_id)


class OccupantMoveView(PermissionRequiredMixin, View):
    """Put someone in a room (or take them out, with an empty room). Answers in JSON,
    for the configurator's drag and drop."""

    permission_required = "tabere.change_room"
    http_method_names = ["post"]

    def post(self, request, pk):
        camp = get_object_or_404(Camp, pk=pk)
        kind, _, occupant_id = request.POST.get("occupant", "").partition("-")
        room_id = request.POST.get("room", "")
        won = {"opportunity__camp": camp, "opportunity__status": Status.WON}
        if kind == "copil" and occupant_id.isdigit():
            occupant = Child.objects.filter(pk=occupant_id, **won).first()
            field = "room"
        elif kind == "adult" and occupant_id.isdigit():
            occupant = camp.opportunities.filter(
                pk=occupant_id, status=Status.WON, contact_goes=True
            ).first()
            field = "contact_room"
        else:
            occupant = None
        if occupant is None:
            return JsonResponse({"error": "Persoana nu mai e în această tabără."}, status=404)
        room = None
        if room_id:
            room = camp.rooms.filter(pk=room_id if room_id.isdigit() else None).first()
            if room is None:
                return JsonResponse({"error": "Camera nu mai există."}, status=404)
            taken = room.children.count() + room.adults.count()
            if getattr(occupant, f"{field}_id") != room.pk and taken >= room.capacity:
                return JsonResponse({"error": f"{room.name} e plină."}, status=409)
        setattr(occupant, field, room)
        occupant.save(update_fields=[field])
        return JsonResponse({"room": room.pk if room else None})


class RoomsExcelView(PermissionRequiredMixin, View):
    """The rooms and who sleeps in each, as an Excel file (with the medical notes, for the
    team at the camp)."""

    permission_required = "tabere.view_room"

    COLUMNS = [
        ("Camera", 14),
        ("Locuri", 8),
        ("Nume", 26),
        ("Cine", 18),
        ("Vârsta", 8),
        ("Oraș", 16),
        ("Părinte / profesor", 24),
        ("Telefon", 16),
        ("Probleme medicale", 40),
    ]

    def get(self, request, pk):
        camp = get_object_or_404(Camp, pk=pk)
        participants = participants_of(camp)
        rooms = rooms_with_occupants(camp, participants)
        phones = {o.key: p.contact.phone for p in participants for o in p.occupants}

        sheet_book = Workbook()
        sheet = sheet_book.active
        sheet.title = "Camere"
        sheet.append([title for title, _ in self.COLUMNS])
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for index, (_, width) in enumerate(self.COLUMNS, start=1):
            sheet.column_dimensions[sheet.cell(row=1, column=index).column_letter].width = width
        sheet.freeze_panes = "A2"

        def row(room_name, capacity, occupant):
            child = occupant.child if occupant else None
            return [
                room_name,
                capacity,
                occupant.name if occupant else "",
                ("Copil" if child else "Părinte / profesor") if occupant else "",
                child.age if child else None,
                child.city if child else "",
                occupant.family if occupant else "",
                phones.get(occupant.key, "") if occupant else "",
                child.medical_notes if child else "",
            ]

        for room in rooms:
            for occupant in room.occupants or [None]:
                sheet.append(row(room.name, room.capacity, occupant))
        unplaced = [o for p in participants for o in p.occupants if o.room_id is None]
        for occupant in unplaced:
            sheet.append(row("Fără cameră", None, occupant))

        output = BytesIO()
        sheet_book.save(output)
        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = f"cazare-{slugify(camp.name) or camp.pk}.xlsx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
