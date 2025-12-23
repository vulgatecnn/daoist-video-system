"""
URL configuration for daoist_video_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import error_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/videos/", include("videos.urls")),
    # 错误报告和监控API
    path("api/monitoring/errors/", error_views.error_statistics, name="error_statistics"),
    path("api/monitoring/performance/", error_views.performance_statistics, name="performance_statistics"),
    path("api/monitoring/health/", error_views.system_health, name="system_health"),
    path("api/monitoring/force-report/", error_views.force_error_report, name="force_error_report"),
    path("api/monitoring/client-errors/", error_views.client_error_report, name="client_error_report"),
]

# 开发环境下提供媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
