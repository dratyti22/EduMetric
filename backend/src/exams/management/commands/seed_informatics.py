from django.core.management.base import BaseCommand
from django.db import transaction
from exams.models import ExamTemplate, ExamTemplateTask, ScoreConversion
from school.models import Subject

INFORMATICS_SCALE = {
    0: 0,
    1: 7,
    2: 14,
    3: 20,
    4: 27,
    5: 34,
    6: 40,
    7: 43,
    8: 46,
    9: 48,
    10: 51,
    11: 54,
    12: 56,
    13: 59,
    14: 62,
    15: 64,
    16: 67,
    17: 70,
    18: 72,
    19: 75,
    20: 78,
    21: 80,
    22: 83,
    23: 85,
    24: 88,
    25: 90,
    26: 93,
    27: 95,
    28: 98,
    29: 100,
}


class Command(BaseCommand):
    help = "Создать или обновить шаблон ЕГЭ по информатике со шкалой перевода баллов"

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=2026)

    @transaction.atomic
    def handle(self, *args, **options):
        year = options["year"]
        template, created = ExamTemplate.objects.get_or_create(
            subject=Subject.INFORMATICS,
            year=year,
        )

        for number in range(1, 28):
            max_score = 2 if number in (26, 27) else 1
            ExamTemplateTask.objects.update_or_create(
                template=template,
                number=number,
                defaults={"max_score": max_score},
            )

        for primary_score, test_score in INFORMATICS_SCALE.items():
            ScoreConversion.objects.update_or_create(
                template=template,
                primary_score=primary_score,
                defaults={"test_score": test_score},
            )

        action = "Создан" if created else "Обновлён"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} шаблон информатики {year}: 27 заданий, шкала 0–29 (до 100 баллов)."
            )
        )
