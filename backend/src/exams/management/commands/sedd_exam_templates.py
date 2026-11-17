from django.core.management.base import BaseCommand
from django.db import transaction
from exams.models import ExamTemplate, ExamTemplateTask, ScoreConversion
from school.enum import Subject

TEMPLATES = {
    # ── Математика (профиль) 2026 ──
    Subject.MATH_PROFILE: {
        "year": 2026,
        "title": "ЕГЭ Математика (профиль) 2026",
        "default_passing_secondary": 27,
        "tasks": (
            [(n, 1) for n in range(1, 13)]
            + [(13, 2), (14, 3), (15, 2), (16, 2), (17, 3), (18, 4), (19, 4)]
        ),
        # max primary = 32
        "scale": {
            0: 0,
            1: 6,
            2: 11,
            3: 17,
            4: 22,
            5: 27,
            6: 34,
            7: 40,
            8: 46,
            9: 52,
            10: 58,
            11: 64,
            12: 70,
            13: 72,
            14: 74,
            15: 76,
            16: 78,
            17: 80,
            18: 82,
            19: 84,
            20: 86,
            21: 88,
            22: 90,
            23: 92,
            24: 94,
            25: 95,
            26: 96,
            27: 97,
            28: 98,
            29: 99,
            30: 100,
            31: 100,
            32: 100,
        },
    },
    # ── Русский язык 2026 ──
    Subject.RUSSIAN: {
        "year": 2026,
        "title": "ЕГЭ Русский язык 2026",
        "default_passing_secondary": 36,
        "tasks": (
            [(n, 1) for n in range(1, 8)]
            + [(8, 2)]
            + [(n, 1) for n in range(9, 26)]
            + [(26, 3), (27, 21)]  # 27 — сочинение
        ),
        # max primary = 50
        "scale": {
            0: 0,
            1: 3,
            2: 5,
            3: 8,
            4: 10,
            5: 12,
            6: 15,
            7: 17,
            8: 20,
            9: 22,
            10: 24,
            11: 27,
            12: 29,
            13: 32,
            14: 34,
            15: 36,
            16: 37,
            17: 39,
            18: 40,
            19: 42,
            20: 43,
            21: 45,
            22: 46,
            23: 48,
            24: 49,
            25: 51,
            26: 52,
            27: 54,
            28: 55,
            29: 57,
            30: 58,
            31: 60,
            32: 61,
            33: 63,
            34: 64,
            35: 66,
            36: 67,
            37: 69,
            38: 70,
            39: 72,
            40: 73,
            41: 75,
            42: 78,
            43: 81,
            44: 83,
            45: 86,
            46: 89,
            47: 91,
            48: 94,
            49: 97,
            50: 100,
        },
    },
    # ── Информатика 2026 ──
    Subject.INFORMATICS: {
        "year": 2026,
        "title": "ЕГЭ Информатика 2026",
        "default_passing_secondary": 40,
        "tasks": [(n, 1) for n in range(1, 26)] + [(26, 2), (27, 2)],
        # max primary = 29
        "scale": {
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
        },
    },
    # ── Физика 2026 ──
    Subject.PHYSICS: {
        "year": 2026,
        "title": "ЕГЭ Физика 2026",
        "default_passing_secondary": 36,
        "tasks": (
            # 1–20: в основном по 1, некоторые по 2
            [
                (1, 1),
                (2, 2),
                (3, 1),
                (4, 1),
                (5, 1),
                (6, 2),
                (7, 1),
                (8, 1),
                (9, 1),
                (10, 1),
                (11, 1),
                (12, 2),
                (13, 1),
                (14, 1),
                (15, 1),
                (16, 1),
                (17, 2),
                (18, 1),
                (19, 1),
                (20, 1),
            ]
            + [(21, 3), (22, 2), (23, 3), (24, 3), (25, 3), (26, 4)]
        ),
        # max primary ≈ 45
        "scale": {
            0: 0,
            1: 4,
            2: 8,
            3: 11,
            4: 15,
            5: 19,
            6: 22,
            7: 26,
            8: 30,
            9: 33,
            10: 36,
            11: 38,
            12: 40,
            13: 42,
            14: 44,
            15: 46,
            16: 48,
            17: 50,
            18: 52,
            19: 54,
            20: 56,
            21: 58,
            22: 60,
            23: 62,
            24: 64,
            25: 66,
            26: 68,
            27: 70,
            28: 72,
            29: 74,
            30: 76,
            31: 78,
            32: 80,
            33: 82,
            34: 84,
            35: 86,
            36: 88,
            37: 90,
            38: 92,
            39: 94,
            40: 96,
            41: 98,
            42: 100,
            43: 100,
            44: 100,
            45: 100,
        },
    },
    # ── Обществознание 2026 ──
    Subject.SOCIAL: {
        "year": 2026,
        "title": "ЕГЭ Обществознание 2026",
        "default_passing_secondary": 42,
        "tasks": (
            [(n, 2) for n in range(1, 17)]
            + [(17, 2), (18, 2), (19, 3), (20, 3), (21, 3), (22, 4), (23, 3), (24, 4), (25, 6)]
        ),
        # max primary = 58
        "scale": {
            0: 0,
            1: 3,
            2: 5,
            3: 8,
            4: 10,
            5: 13,
            6: 15,
            7: 18,
            8: 20,
            9: 22,
            10: 25,
            11: 27,
            12: 30,
            13: 32,
            14: 34,
            15: 37,
            16: 39,
            17: 42,
            18: 44,
            19: 46,
            20: 48,
            21: 50,
            22: 52,
            23: 54,
            24: 55,
            25: 57,
            26: 58,
            27: 60,
            28: 61,
            29: 63,
            30: 64,
            31: 66,
            32: 67,
            33: 69,
            34: 70,
            35: 72,
            36: 73,
            37: 75,
            38: 77,
            39: 79,
            40: 81,
            41: 83,
            42: 85,
            43: 88,
            44: 90,
            45: 92,
            46: 94,
            47: 96,
            48: 98,
            49: 100,
            50: 100,
            51: 100,
            52: 100,
            53: 100,
            54: 100,
            55: 100,
            56: 100,
            57: 100,
            58: 100,
        },
    },
    # ── Биология 2026 (упрощённо, шкала пропорциональная если нет точной) ──
    Subject.BIOLOGY: {
        "year": 2026,
        "title": "ЕГЭ Биология 2026",
        "default_passing_secondary": 36,
        "tasks": [(n, 1) for n in range(1, 22)] + [(n, 3) for n in range(22, 29)],
        "scale": {},  # будет пропорциональный пересчёт
    },
    # ── Химия 2026 ──
    Subject.CHEMISTRY: {
        "year": 2026,
        "title": "ЕГЭ Химия 2026",
        "default_passing_secondary": 36,
        "tasks": [(n, 1) for n in range(1, 29)] + [(n, 3) for n in range(29, 35)],
        "scale": {},
    },
    # ── История 2026 ──
    Subject.HISTORY: {
        "year": 2026,
        "title": "ЕГЭ История 2026",
        "default_passing_secondary": 32,
        "tasks": [(n, 1) for n in range(1, 13)] + [(n, 3) for n in range(13, 22)],
        "scale": {},
    },
    # ── Английский язык 2026 ──
    Subject.ENGLISH: {
        "year": 2026,
        "title": "ЕГЭ Английский язык 2026",
        "default_passing_secondary": 22,
        "tasks": [(n, 1) for n in range(1, 39)],
        "scale": {},
    },
}


class Command(BaseCommand):
    help = "Создать / обновить шаблоны ЕГЭ по всем предметам с заданиями и шкалами перевода"

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=2026,
            help="Год шаблонов (по умолчанию 2026)",
        )
        parser.add_argument(
            "--subject",
            type=str,
            default=None,
            help="Только один предмет (например math_profile). Если не указан — все.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        year = options["year"]
        only_subject = options["subject"]

        created_count = 0
        updated_count = 0

        for subject, data in TEMPLATES.items():
            if only_subject and subject != only_subject:
                continue

            template, created = ExamTemplate.objects.update_or_create(
                subject=subject,
                year=year,
                defaults={
                    "title": data["title"].replace("2026", str(year)),
                    "default_passing_secondary": data["default_passing_secondary"],
                },
            )

            # Задания
            ExamTemplateTask.objects.filter(template=template).delete()
            ExamTemplateTask.objects.bulk_create(
                [
                    ExamTemplateTask(
                        template=template,
                        number=number,
                        max_score=max_score,
                    )
                    for number, max_score in data["tasks"]
                ]
            )

            # Шкала перевода
            ExamTemplateTask  # noqa — просто чтобы не ругался линтер
            ScoreConversion.objects.filter(template=template).delete()
            if data["scale"]:
                ScoreConversion.objects.bulk_create(
                    [
                        ScoreConversion(
                            template=template,
                            primary_score=primary,
                            test_score=test,
                        )
                        for primary, test in data["scale"].items()
                    ]
                )
            if created:
                created_count += 1
                action = "Создан"
            else:
                updated_count += 1
                action = "Обновлён"

            max_primary = sum(m for _, m in data["tasks"])
            scale_info = (
                f"шкала 0–{max(data['scale'])}" if data["scale"] else "пропорциональная шкала"
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action}: {template.get_subject_display()} {year} "
                    f"({len(data['tasks'])} заданий, макс. {max_primary} перв., {scale_info})"
                )
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Готово. Создано: {created_count}, обновлено: {updated_count}.")
        )
