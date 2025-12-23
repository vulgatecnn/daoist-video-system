#!/usr/bin/env python
"""
测试管理员登录
"""
import requests
import json

# API基础URL
BASE_URL = 'http://127.0.0.1:8000/api/auth'

def test_admin_login():
    """测试管理员登录"""
    print("测试管理员登录...")
    
    # 登录数据
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    try:
        response = requests.post(f'{BASE_URL}/login/', json=login_data)
        print(f"管理员登录响应状态码: {response.status_code}")
        print(f"管理员登录响应内容: {response.json()}")
        
        if response.status_code == 200:
            print("✅ 管理员登录成功")
            
            # 测试管理员权限
            token = response.json()['tokens']['access']
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # 测试权限检查
            perm_response = requests.get(f'{BASE_URL}/check-permission/', headers=headers)
            print(f"权限检查响应: {perm_response.json()}")
            
            # 测试管理员用户列表
            users_response = requests.get(f'{BASE_URL}/admin/users/', headers=headers)
            print(f"用户列表响应状态码: {users_response.status_code}")
            if users_response.status_code == 200:
                print("✅ 管理员可以访问用户列表")
            else:
                print("❌ 管理员无法访问用户列表")
                
            return response.json()
        else:
            print("❌ 管理员登录失败")
            return None
    except Exception as e:
        print(f"❌ 管理员登录请求失败: {e}")
        return None

if __name__ == '__main__':
    test_admin_login()