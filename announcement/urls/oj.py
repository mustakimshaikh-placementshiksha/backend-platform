# from django.conf.urls import url

# from ..views.oj import AnnouncementAPI

# urlpatterns = [
#     url(r"^announcement/?$", AnnouncementAPI.as_view(), name="announcement_api"),
# ]
# announcement/urls/oj.py
from django.urls import path

from ..views.oj import (
    AnnouncementAPI,
    AnnouncementListAPI,
)

urlpatterns = [
    path("", AnnouncementListAPI.as_view(), name="announcement_list_api"),
    path("<int:pk>/", AnnouncementAPI.as_view(), name="announcement_api"),
]