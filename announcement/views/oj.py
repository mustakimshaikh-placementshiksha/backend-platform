from utils.api import APIView

from announcement.models import Announcement
from announcement.serializers import AnnouncementSerializer



from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class AnnouncementListAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Retrieves a list of system announcements.

    Logic Flow:
    - Filters for visible announcements only.
    - Returns paginated results to the user.
    """
    @swagger_auto_schema(
        operation_summary="Get Announcement List",
        manual_parameters=[
            openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Limit"),
            openapi.Parameter("offset", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Offset"),
        ],
        responses={200: AnnouncementSerializer(many=True)},
        tags=["Announcement"]
    )
    def get(self, request):
        announcements = Announcement.objects.filter(visible=True)
        return self.success(self.paginate_data(request, announcements, AnnouncementSerializer))


class AnnouncementAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Retrieves details of a specific announcement.

    Logic Flow:
    - Fetches announcement by ID, ensuring it is marked as visible.
    - Returns the serialized announcement data.
    """
    @swagger_auto_schema(
        operation_summary="Get Announcement Detail",
        responses={200: AnnouncementSerializer},
        tags=["Announcement"]
    )
    def get(self, request, pk):
        try:
            announcement = Announcement.objects.get(id=pk, visible=True)
            return self.success(AnnouncementSerializer(announcement).data)
        except Announcement.DoesNotExist:
            return self.error("Announcement does not exist")
