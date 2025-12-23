from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """扩展的用户模型"""
    
    # 用户角色选择
    ROLE_CHOICES = [
        ('admin', '管理员'),
        ('user', '普通用户'),
    ]
    
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES, 
        default='user',
        verbose_name="用户角色"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"
        
    def is_admin(self):
        """检查是否为管理员"""
        return self.role == 'admin'
        
    def is_regular_user(self):
        """检查是否为普通用户"""
        return self.role == 'user'
