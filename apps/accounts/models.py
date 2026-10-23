from django.contrib.auth.models import AbstractUser


# Custom user model from day one: swapping it after the first migration is painful.
class User(AbstractUser):
    pass
