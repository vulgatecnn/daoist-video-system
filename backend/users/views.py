"""
用户认证相关的视图
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import login, logout
from .models import User
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserProfileSerializer,
    UserUpdateSerializer
)
from .permissions import IsAdmin


class CustomTokenObtainPairView(TokenObtainPairView):
    """自定义JWT令牌获取视图"""
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            # 获取用户信息
            serializer = UserLoginSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                user_data = UserProfileSerializer(user).data
                response.data['user'] = user_data
        return response


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """用户注册视图"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # 生成JWT令牌
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # 返回用户信息和令牌
        user_data = UserProfileSerializer(user).data
        
        return Response({
            'message': '注册成功',
            'user': user_data,
            'tokens': {
                'access': str(access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """用户登录视图"""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # 生成JWT令牌
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # 返回用户信息和令牌
        user_data = UserProfileSerializer(user).data
        
        return Response({
            'message': '登录成功',
            'user': user_data,
            'tokens': {
                'access': str(access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """用户登出视图"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'message': '登出成功'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': '登出失败'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """获取用户资料"""
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    """更新用户资料"""
    serializer = UserUpdateSerializer(
        request.user, 
        data=request.data, 
        partial=request.method == 'PATCH'
    )
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': '资料更新成功',
            'user': UserProfileSerializer(request.user).data
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_users_list_view(request):
    """管理员获取用户列表"""
    users = User.objects.all().order_by('-created_at')
    serializer = UserProfileSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_permission_view(request):
    """检查用户权限"""
    user = request.user
    return Response({
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'is_admin': user.is_admin(),
        'is_regular_user': user.is_regular_user(),
        'permissions': {
            'can_upload_video': user.is_admin(),
            'can_manage_videos': user.is_admin(),
            'can_view_videos': True,
            'can_compose_videos': True,
        }
    })
