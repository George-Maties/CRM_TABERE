from django.views.generic import TemplateView


class WelcomeView(TemplateView):
    template_name = "contacte/welcome.html"
