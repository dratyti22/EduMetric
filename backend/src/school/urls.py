from django.urls import path, include
from rest_framework.routers import DefaultRouter

from school.views import SchoolClassView

router = DefaultRouter()
router.register("classes", SchoolClassView, basename="school")

urlpatterns = [
    path("", include(router.urls))
]

