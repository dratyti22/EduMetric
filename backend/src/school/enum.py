from django.db import models


class Subject(models.TextChoices):
    MATH_PROFILE = "math_profile", "Математика (профиль)"
    MATH_BASE = "math_base", "Математика (база)"
    RUSSIAN = "russian", "Русский язык"
    INFORMATICS = "informatics", "Информатика"
    PHYSICS = "physics", "Физика"
    SOCIAL = "social", "Обществознание"
    BIOLOGY = "biology", "Биология"
    CHEMISTRY = "chemistry", "Химия"
    HISTORY = "history", "История"
    ENGLISH = "english", "Английский язык"
