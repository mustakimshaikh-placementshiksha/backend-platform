"""
utils/views.py

Simditor rich-text editor upload endpoints.
Both accept multipart/form-data POST requests and return a JSON response
that the Simditor JavaScript SDK understands.
"""

import os

from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import MultiPartParser, FormParser

from account.serializers import ImageUploadForm, FileUploadForm
from utils.shortcuts import rand_str
from utils.api import CSRFExemptAPIView
import logging

logger = logging.getLogger(__name__)


# ─── Response schema shared by both upload endpoints ─────────────────────────

_UPLOAD_RESPONSE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    description="Simditor-compatible upload result",
    properties={
        "success":   openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                    description="True if upload succeeded"),
        "msg":       openapi.Schema(type=openapi.TYPE_STRING,
                                    description="Human-readable status message"),
        "file_path": openapi.Schema(type=openapi.TYPE_STRING,
                                    description="Public URL path of the uploaded file"),
    },
    required=["success", "msg", "file_path"],
)

_FILE_UPLOAD_RESPONSE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    description="Simditor-compatible file upload result",
    properties={
        "success":   openapi.Schema(type=openapi.TYPE_BOOLEAN),
        "msg":       openapi.Schema(type=openapi.TYPE_STRING),
        "file_path": openapi.Schema(type=openapi.TYPE_STRING,
                                    description="Public URL path of the uploaded file"),
        "file_name": openapi.Schema(type=openapi.TYPE_STRING,
                                    description="Original filename"),
    },
    required=["success", "msg"],
)


class SimditorImageUploadAPIView(CSRFExemptAPIView):
    """
    **POST** `/api/utils/admin/upload_image/`

    Upload an image to be embedded inside the Simditor rich-text editor.

    ### Accepted Formats
    `.gif`, `.jpg`, `.jpeg`, `.bmp`, `.png`

    ### Auth
    Session cookie (must be logged in).

    ### Returns
    A JSON object consumed directly by the Simditor JS SDK:
    ```json
    { "success": true, "msg": "Success", "file_path": "/public/upload/<name>" }
    ```
    """
    parser_classes = [MultiPartParser, FormParser]
    request_parsers = ()

    @swagger_auto_schema(
        operation_id="utils_upload_image",
        operation_summary="Upload Image (Simditor)",
        operation_description=(
            "Upload an image file that will be embedded in the Simditor rich-text editor.\n\n"
            "**Allowed formats:** `.gif`, `.jpg`, `.jpeg`, `.bmp`, `.png`\n\n"
            "Returns a Simditor-compatible JSON response with `success`, `msg`, and `file_path`."
        ),
        manual_parameters=[
            openapi.Parameter(
                "image",
                openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="Image file to upload (max ~10 MB, gif/jpg/jpeg/bmp/png only)"
            )
        ],
        consumes=["multipart/form-data"],
        responses={
            200: openapi.Response(
                description="Upload result – check `success` field",
                schema=_UPLOAD_RESPONSE_SCHEMA,
                examples={
                    "application/json": {
                        "success": True,
                        "msg": "Success",
                        "file_path": "/public/upload/abcde12345.png"
                    }
                }
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Utils (Upload)"]
    )
    def post(self, request):
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            img = form.cleaned_data["image"]
        else:
            return self.response({
                "success": False,
                "msg": "Upload failed – invalid form data",
                "file_path": ""})

        suffix = os.path.splitext(img.name)[-1].lower()
        if suffix not in [".gif", ".jpg", ".jpeg", ".bmp", ".png"]:
            return self.response({
                "success": False,
                "msg": f"Unsupported file format '{suffix}'. Allowed: gif, jpg, jpeg, bmp, png",
                "file_path": ""})

        img_name = rand_str(10) + suffix
        try:
            with open(os.path.join(settings.UPLOAD_DIR, img_name), "wb") as imgFile:
                for chunk in img:
                    imgFile.write(chunk)
        except IOError as e:
            logger.error(e)
            return self.response({
                "success": False,
                "msg": "Upload Error – could not write file to disk",
                "file_path": ""})

        return self.response({
            "success": True,
            "msg": "Success",
            "file_path": f"{settings.UPLOAD_PREFIX}/{img_name}"})


class SimditorFileUploadAPIView(CSRFExemptAPIView):
    """
    **POST** `/api/utils/admin/upload_file/`

    Upload a generic file to be linked from the Simditor rich-text editor.

    ### Auth
    Session cookie (must be logged in).

    ### Returns
    ```json
    { "success": true, "msg": "Success",
      "file_path": "/public/upload/<name>", "file_name": "original.pdf" }
    ```
    """
    parser_classes = [MultiPartParser, FormParser]
    request_parsers = ()

    @swagger_auto_schema(
        operation_id="utils_upload_file",
        operation_summary="Upload File (Simditor)",
        operation_description=(
            "Upload a generic file (PDF, DOCX, etc.) that will be linked inside the "
            "Simditor rich-text editor.\n\n"
            "Returns a Simditor-compatible JSON response with `success`, `msg`, `file_path`, "
            "and `file_name`."
        ),
        manual_parameters=[
            openapi.Parameter(
                "file",
                openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="File to upload"
            )
        ],
        consumes=["multipart/form-data"],
        responses={
            200: openapi.Response(
                description="Upload result – check `success` field",
                schema=_FILE_UPLOAD_RESPONSE_SCHEMA,
                examples={
                    "application/json": {
                        "success": True,
                        "msg": "Success",
                        "file_path": "/public/upload/abcde12345.pdf",
                        "file_name": "assignment.pdf"
                    }
                }
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Utils (Upload)"]
    )
    def post(self, request):
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
        else:
            return self.response({
                "success": False,
                "msg": "Upload failed – invalid form data"
            })

        suffix = os.path.splitext(file.name)[-1].lower()
        file_name = rand_str(10) + suffix
        try:
            with open(os.path.join(settings.UPLOAD_DIR, file_name), "wb") as f:
                for chunk in file:
                    f.write(chunk)
        except IOError as e:
            logger.error(e)
            return self.response({
                "success": False,
                "msg": "Upload Error – could not write file to disk"})

        return self.response({
            "success": True,
            "msg": "Success",
            "file_path": f"{settings.UPLOAD_PREFIX}/{file_name}",
            "file_name": file.name})
