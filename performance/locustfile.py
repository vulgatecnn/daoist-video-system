"""
性能测试配置文件 - 使用 Locust 进行负载测试
"""

import json
import random
import time
from locust import HttpUser, task, between
from locust.exception import RescheduleTask


class DaoistVideoSystemUser(HttpUser):
    """道教视频系统用户行为模拟"""
    
    wait_time = between(1, 3)  # 用户操作间隔时间
    
    def on_start(self):
        """用户开始测试时的初始化操作"""
        self.login()
    
    def login(self):
        """用户登录"""
        login_data = {
            "username": f"test_user_{random.randint(1, 100)}",
            "password": "test_password"
        }
        
        with self.client.post("/api/auth/login/", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                # 保存认证令牌
                self.token = response.json().get("token")
                self.client.headers.update({"Authorization": f"Bearer {self.token}"})
                response.success()
            else:
                response.failure(f"登录失败: {response.status_code}")
    
    @task(3)
    def view_homepage(self):
        """访问首页"""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"首页访问失败: {response.status_code}")
    
    @task(2)
    def health_check(self):
        """健康检查"""
        with self.client.get("/health/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"健康检查失败: {response.status_code}")
    
    @task(5)
    def list_videos(self):
        """获取视频列表"""
        params = {
            "page": random.randint(1, 5),
            "page_size": 20
        }
        
        with self.client.get("/api/videos/", params=params, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "results" in data:
                    response.success()
                else:
                    response.failure("视频列表格式错误")
            else:
                response.failure(f"获取视频列表失败: {response.status_code}")
    
    @task(3)
    def view_video_detail(self):
        """查看视频详情"""
        video_id = random.randint(1, 100)
        
        with self.client.get(f"/api/videos/{video_id}/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # 404 是正常的，因为我们使用随机 ID
                response.success()
            else:
                response.failure(f"查看视频详情失败: {response.status_code}")
    
    @task(1)
    def search_videos(self):
        """搜索视频"""
        search_terms = ["道教", "太极", "修行", "仙术", "丹药", "符咒"]
        search_query = random.choice(search_terms)
        
        params = {"search": search_query}
        
        with self.client.get("/api/videos/search/", params=params, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"搜索视频失败: {response.status_code}")
    
    @task(1)
    def upload_video(self):
        """上传视频 (模拟)"""
        # 模拟文件上传，不实际上传大文件
        video_data = {
            "title": f"测试视频_{random.randint(1, 1000)}",
            "description": "这是一个性能测试视频",
            "category": "修行指导"
        }
        
        with self.client.post("/api/videos/upload/", json=video_data, catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 401:
                # 未授权是正常的，因为我们可能没有上传权限
                response.success()
            else:
                response.failure(f"上传视频失败: {response.status_code}")
    
    @task(2)
    def get_user_profile(self):
        """获取用户资料"""
        with self.client.get("/api/user/profile/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                # 重新登录
                self.login()
                raise RescheduleTask()
            else:
                response.failure(f"获取用户资料失败: {response.status_code}")
    
    @task(1)
    def video_composition_status(self):
        """检查视频合成状态"""
        task_id = f"task_{random.randint(1, 100)}"
        
        with self.client.get(f"/api/composition/status/{task_id}/", catch_response=True) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"检查合成状态失败: {response.status_code}")


class AdminUser(HttpUser):
    """管理员用户行为模拟"""
    
    wait_time = between(2, 5)
    weight = 1  # 管理员用户权重较低
    
    def on_start(self):
        """管理员登录"""
        login_data = {
            "username": "admin",
            "password": "admin_password"
        }
        
        with self.client.post("/api/auth/login/", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                self.token = response.json().get("token")
                self.client.headers.update({"Authorization": f"Bearer {self.token}"})
                response.success()
            else:
                response.failure(f"管理员登录失败: {response.status_code}")
    
    @task(2)
    def admin_dashboard(self):
        """访问管理员仪表板"""
        with self.client.get("/api/admin/dashboard/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"管理员仪表板访问失败: {response.status_code}")
    
    @task(1)
    def system_stats(self):
        """获取系统统计信息"""
        with self.client.get("/api/admin/stats/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"获取系统统计失败: {response.status_code}")
    
    @task(1)
    def manage_users(self):
        """管理用户"""
        with self.client.get("/api/admin/users/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"管理用户失败: {response.status_code}")


class HeavyLoadUser(HttpUser):
    """重负载用户 - 模拟视频处理等重操作"""
    
    wait_time = between(5, 10)
    weight = 1  # 重负载用户权重较低
    
    @task(1)
    def video_processing(self):
        """视频处理任务"""
        processing_data = {
            "video_id": random.randint(1, 50),
            "operation": random.choice(["compress", "watermark", "trim"]),
            "parameters": {
                "quality": random.choice(["high", "medium", "low"]),
                "format": random.choice(["mp4", "avi", "mov"])
            }
        }
        
        with self.client.post("/api/videos/process/", json=processing_data, catch_response=True) as response:
            if response.status_code in [200, 202]:  # 202 表示已接受处理
                response.success()
            else:
                response.failure(f"视频处理失败: {response.status_code}")
    
    @task(1)
    def batch_operations(self):
        """批量操作"""
        batch_data = {
            "video_ids": [random.randint(1, 100) for _ in range(5)],
            "operation": "batch_update",
            "data": {"category": "批量更新测试"}
        }
        
        with self.client.post("/api/videos/batch/", json=batch_data, catch_response=True) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"批量操作失败: {response.status_code}")


# 性能测试配置
class WebsiteUser(HttpUser):
    """网站用户 - 主要测试前端页面"""
    
    tasks = [DaoistVideoSystemUser]
    min_wait = 1000
    max_wait = 3000
    
    @task(10)
    def index_page(self):
        """首页"""
        self.client.get("/")
    
    @task(5)
    def static_files(self):
        """静态文件"""
        static_files = [
            "/static/css/main.css",
            "/static/js/main.js",
            "/static/images/logo.png"
        ]
        
        for file_path in static_files:
            self.client.get(file_path)
    
    @task(3)
    def api_endpoints(self):
        """API 端点"""
        endpoints = [
            "/api/videos/",
            "/api/categories/",
            "/health/"
        ]
        
        for endpoint in endpoints:
            self.client.get(endpoint)


# 自定义事件监听器
from locust import events

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时的回调"""
    print("🚀 性能测试开始...")
    print(f"目标主机: {environment.host}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时的回调"""
    print("✅ 性能测试完成")
    
    # 输出测试结果摘要
    stats = environment.stats
    print(f"总请求数: {stats.total.num_requests}")
    print(f"失败请求数: {stats.total.num_failures}")
    print(f"平均响应时间: {stats.total.avg_response_time:.2f}ms")
    print(f"95% 响应时间: {stats.total.get_response_time_percentile(0.95):.2f}ms")

@events.request_failure.add_listener
def on_request_failure(request_type, name, response_time, response_length, exception, **kwargs):
    """请求失败时的回调"""
    print(f"❌ 请求失败: {request_type} {name} - {exception}")

# 性能基准检查
@events.test_stop.add_listener
def check_performance_benchmarks(environment, **kwargs):
    """检查性能基准"""
    stats = environment.stats.total
    
    # 定义性能基准
    benchmarks = {
        "max_avg_response_time": 2000,  # 平均响应时间不超过 2 秒
        "max_95_percentile": 5000,      # 95% 响应时间不超过 5 秒
        "max_failure_rate": 0.05,       # 失败率不超过 5%
    }
    
    # 检查基准
    avg_response_time = stats.avg_response_time
    percentile_95 = stats.get_response_time_percentile(0.95)
    failure_rate = stats.num_failures / stats.num_requests if stats.num_requests > 0 else 0
    
    print("\n📊 性能基准检查:")
    
    if avg_response_time <= benchmarks["max_avg_response_time"]:
        print(f"✅ 平均响应时间: {avg_response_time:.2f}ms (基准: {benchmarks['max_avg_response_time']}ms)")
    else:
        print(f"❌ 平均响应时间超标: {avg_response_time:.2f}ms (基准: {benchmarks['max_avg_response_time']}ms)")
    
    if percentile_95 <= benchmarks["max_95_percentile"]:
        print(f"✅ 95% 响应时间: {percentile_95:.2f}ms (基准: {benchmarks['max_95_percentile']}ms)")
    else:
        print(f"❌ 95% 响应时间超标: {percentile_95:.2f}ms (基准: {benchmarks['max_95_percentile']}ms)")
    
    if failure_rate <= benchmarks["max_failure_rate"]:
        print(f"✅ 失败率: {failure_rate:.2%} (基准: {benchmarks['max_failure_rate']:.2%})")
    else:
        print(f"❌ 失败率超标: {failure_rate:.2%} (基准: {benchmarks['max_failure_rate']:.2%})")