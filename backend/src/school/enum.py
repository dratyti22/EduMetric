from django.db import models


class Subject(models.TextChoices):
    RUSSIAN = "russian", "Русский язык"
    INFORMATICS = "informatics", "Информатика"
    MATH_PROFILE = "math_profile", "Профильная математика"
