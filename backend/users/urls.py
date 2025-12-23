"""
用户认证相关的URL配置
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'users'

urlpatterns = [
    # JWT认证
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # 用户资料
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile_view, name='update_profile'),
    
    # 权限检查
    path('check-permission/', views.check_permission_view, name='check_permission'),
    
    # 管理员功能
    path('admin/users/', views.admin_users_list_view, name='admin_users_list'),
]