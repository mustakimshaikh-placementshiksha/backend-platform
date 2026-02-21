"""
oj/urls.py

Root URL configuration for the OnlineJudge project.

API groups:
  • Account     – /api/account/          (public)   /api/account/admin/   (super-admin)
  • Announcement– /api/announcement/     (public)   /api/announcement/admin/
  • System Conf – /api/conf/             (public)   /api/conf/admin/
  • Problem     – /api/problem/          (public)   /api/problem/admin/
  • Contest     – /api/contest/          (public)   /api/contest/admin/
  • Submission  – /api/submission/       (auth)     /api/submission/admin/
  • Utils       – /api/utils/admin/

Swagger UI  → http://localhost:8000/swagger/
ReDoc       → http://localhost:8000/redoc/
Raw JSON    → http://localhost:8000/swagger.json
Raw YAML    → http://localhost:8000/swagger.yaml

Authentication in Swagger:
  • SessionAuth  – regular session cookie (login via /api/account/login/)
  • ApiKeyAuth   – pass APPKEY header with the value from /api/account/appkey/ endpoint
"""

from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# ─── Swagger / OpenAPI Schema View ───────────────────────────────────────────

schema_view = get_schema_view(
    openapi.Info(
        title="OnlineJudge API",
        default_version="v1",
        description="""
## OnlineJudge REST API

A complete backend for competitive-programming online judges.  
Built with **Django 4.2** · **Django REST Framework** · **PostgreSQL** · **Redis**.

---

### Authentication

| Method         | How to use                                                                  |
|----------------|-----------------------------------------------------------------------------|
| **Session**    | POST `/api/account/login/` → session cookie is set automatically            |
| **API Key**    | POST `/api/account/appkey/` → returns `appkey`; pass it as `APPKEY` header  |

> **To test in Swagger UI**: click **Authorize** (top-right) and enter either your  
> `sessionid` cookie **or** your API App Key.

---

### Response Format

Every endpoint wraps its payload in a standard envelope:

```json
{ "error": null,          // null on success, string on failure
  "data":  { ... }        // actual payload
}
```

Paginated list responses:
```json
{ "error": null,
  "data": { "total": 42, "results": [ ... ] }
}
```

---

### Tags / Modules

| Tag                   | Description                                     |
|-----------------------|-------------------------------------------------|
| **Account**           | Login, register, profile, password management   |
| **Security**          | 2FA, sessions, API key management               |
| **SSO**               | Single Sign-On token exchange                   |
| **Rank**              | Global user leaderboard                         |
| **Admin**             | Super-admin user management                     |
| **Announcement**      | Public system announcements                     |
| **Announcement Admin**| Admin create/edit/delete announcements          |
| **Problem**           | Browse & fetch problems                         |
| **Problem Admin**     | Create/edit/delete problems, test-case upload   |
| **Contest**           | Browse contests, rankings, submissions          |
| **Contest Admin**     | Create/edit contests, download submissions      |
| **Contest Problem Admin** | Add/edit contest-specific problems          |
| **Submission**        | Submit code, view results                       |
| **Submission Admin**  | Re-judge submissions                            |
| **System Config**     | SMTP, judge servers, website config (admin)     |
| **Utils (Upload)**    | Simditor rich-text editor image/file uploads    |
        """,
        terms_of_service="https://www.placementshiksha.com/terms/",
        contact=openapi.Contact(
            name="PlacementShiksha LLP",
            email="dev@placementshiksha.com",
            url="https://www.placementshiksha.com"
        ),
        license=openapi.License(name="BSD License"),
        x_logo={
            "url": "/public/logo.png",
            "altText": "OnlineJudge Logo"
        },
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# ─── URL Patterns ─────────────────────────────────────────────────────────────

urlpatterns = [

    # ── Account ───────────────────────────────────────────────────────────────
    path("api/account/",        include("account.urls.oj")),
    path("api/account/admin/",  include("account.urls.admin")),

    # ── Announcement ──────────────────────────────────────────────────────────
    path("api/announcement/",        include("announcement.urls.oj")),
    path("api/announcement/admin/",  include("announcement.urls.admin")),

    # ── System Configuration ──────────────────────────────────────────────────
    path("api/conf/",        include("conf.urls.oj")),
    path("api/conf/admin/",  include("conf.urls.admin")),

    # ── Problem ───────────────────────────────────────────────────────────────
    path("api/problem/",        include("problem.urls.oj")),
    path("api/problem/admin/",  include("problem.urls.admin")),

    # ── Contest ───────────────────────────────────────────────────────────────
    path("api/contest/",        include("contest.urls.oj")),
    path("api/contest/admin/",  include("contest.urls.admin")),

    # ── Submission ────────────────────────────────────────────────────────────
    path("api/submission/",        include("submission.urls.oj")),
    path("api/submission/admin/",  include("submission.urls.admin")),

    # ── Utils – editor uploads ────────────────────────────────────────────────
    path("api/utils/admin/", include("utils.urls")),

    # ── Swagger / OpenAPI documentation ──────────────────────────────────────
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]
