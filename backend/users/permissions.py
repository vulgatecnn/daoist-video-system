"""
基于角色的权限控制
"""
from rest_framework import permissions
from functools import wraps
from rest_framework.response import Response
from rest_framework import status


class IsAdmin(permissions.BasePermission):
    """管理员权限"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin()


class IsRegularUser(permissions.BasePermission):
    """普通用户权限"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_regular_user()


class IsAdminOrReadOnly(permissions.BasePermission):
    """管理员可以进行任何操作，其他用户只读"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.is_admin()


def admin_required(view_func):
    """管理员权限装饰器"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'error': '需要登录'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        if not request.user.is_admin():
            return Response(
                {'error': '需要管理员权限'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def user_required(view_func):
    """普通用户权限装饰器"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'error': '需要登录'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return view_func(request, *args, **kwargs)
    return wrapper
