#!/usr/bin/env python
"""
测试用户认证API的脚本
"""
import os
import sys
import django
import requests
import json

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

from users.models import User

# API基础URL
BASE_URL = 'http://127.0.0.1:8000/api/auth'

def test_user_registration():
    """测试用户注册"""
    print("测试用户注册...")
    
    # 创建测试用户数据
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpassword123',
        'password_confirm': 'testpassword123',
        'role': 'user'
    }
    
    try:
        response = requests.post(f'{BASE_URL}/register/', json=user_data)
        print(f"注册响应状态码: {response.status_code}")
        print(f"注册响应内容: {response.json()}")
        
        if response.status_code == 201:
            print("✅ 用户注册成功")
            return response.json()
        else:
            print("❌ 用户注册失败")
            return None
    except Exception as e:
        print(f"❌ 注册请求失败: {e}")
        return None

def test_user_login():
    """测试用户登录"""
    print("\n测试用户登录...")
    
    # 登录数据
    login_data = {
        'username': 'testuser',
        'password': 'testpassword123'
    }
    
    try:
        response = requests.post(f'{BASE_URL}/login/', json=login_data)
        print(f"登录响应状态码: {response.status_code}")
        print(f"登录响应内容: {response.json()}")
        
        if response.status_code == 200:
            print("✅ 用户登录成功")
            return response.json()
        else:
            print("❌ 用户登录失败")
            return None
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return None

def test_admin_login():
    """测试管理员登录"""
    print("\n测试管理员登录...")
    
    # 首先创建管理员用户
    try:
        admin_user = User.objects.get(username='admin')
        admin_user.role = 'admin'
        admin_user.save()
        print("✅ 管理员角色设置成功")
    except User.DoesNotExist:
        print("❌ 管理员用户不存在")
        return None
    
    # 登录数据
    login_data = {
        'username': 'admin',
        'password': '123456'
    }
    
    try:
        response = requests.post(f'{BASE_URL}/login/', json=login_data)
        print(f"管理员登录响应状态码: {response.status_code}")
        print(f"管理员登录响应内容: {response.json()}")
        
        if response.status_code == 200:
            print("✅ 管理员登录成功")
            return response.json()
        else:
            print("❌ 管理员登录失败")
            return None
    except Exception as e:
        print(f"❌ 管理员登录请求失败: {e}")
        return None

def test_protected_endpoint(token):
    """测试受保护的端点"""
    print("\n测试受保护的端点...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # 测试获取用户资料
        response = requests.get(f'{BASE_URL}/profile/', headers=headers)
        print(f"获取资料响应状态码: {response.status_code}")
        print(f"获取资料响应内容: {response.json()}")
        
        if response.status_code == 200:
            print("✅ 受保护端点访问成功")
        else:
            print("❌ 受保护端点访问失败")
            
        # 测试权限检查
        response = requests.get(f'{BASE_URL}/check-permission/', headers=headers)
        print(f"权限检查响应状态码: {response.status_code}")
        print(f"权限检查响应内容: {response.json()}")
        
    except Exception as e:
        print(f"❌ 受保护端点请求失败: {e}")

def main():
    """主测试函数"""
    print("开始测试用户认证API...")
    
    # 清理测试用户
    try:
        User.objects.filter(username='testuser').delete()
        print("清理旧的测试用户")
    except:
        pass
    
    # 测试注册
    register_result = test_user_registration()
    if not register_result:
        return
    
    # 测试登录
    login_result = test_user_login()
    if not login_result:
        return
    
    # 测试受保护端点
    access_token = login_result['tokens']['access']
    test_protected_endpoint(access_token)
    
    # 测试管理员登录
    admin_result = test_admin_login()
    if admin_result:
        admin_token = admin_result['tokens']['access']
        test_protected_endpoint(admin_token)
    
    print("\n✅ 所有测试完成")

if __name__ == '__main__':
    main()