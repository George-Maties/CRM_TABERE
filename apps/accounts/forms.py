from django.contrib.auth.forms import AuthenticationForm

from apps.core.forms import BootstrapFormMixin


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    # Django's Romanian translation spells ț/ș with a cedilla; these are written correctly.
    error_messages = {
        "invalid_login": (
            "Numele de utilizator sau parola nu sunt corecte. "
            "Atenție: se face diferența între literele mari și mici."
        ),
        "inactive": "Acest cont este dezactivat.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Usernames are typed as-is: no autocorrect, capitalisation or spellcheck.
        self.fields["username"].widget.attrs.update(
            {"autocapitalize": "none", "autocorrect": "off", "spellcheck": "false"}
        )
