"""
缓存服务
提供统一的缓存接口和缓存策略
"""
import json
import hashlib
from typing import Any, Optional, Dict, List
from django.core.cache import cache, caches
from django.conf import settings
from django.db.models import QuerySet
from django.core.serializers import serialize
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """缓存服务类"""
    
    def __init__(self, cache_alias: str = 'default'):
        self.cache = caches[cache_alias]
        self.default_timeout = getattr(settings, 'CACHE_DEFAULT_TIMEOUT', 300)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        try:
            return self.cache.get(key, default)
        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {str(e)}")
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            timeout = timeout or self.default_timeout
            return self.cache.set(key, value, timeout)
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            return self.cache.delete(key)
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {str(e)}")
            return False
    
    def get_or_set(self, key: str, callable_func, timeout: Optional[int] = None) -> Any:
        """获取缓存，如果不存在则调用函数设置"""
        try:
            timeout = timeout or self.default_timeout
            return self.cache.get_or_set(key, callable_func, timeout)
        except Exception as e:
            logger.error(f"获取或设置缓存失败 {key}: {str(e)}")
            # 如果缓存失败，直接调用函数
            return callable_func()
    
    def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的缓存"""
        try:
            if hasattr(self.cache, 'delete_pattern'):
                return self.cache.delete_pattern(pattern)
            else:
                # 如果不支持模式删除，记录警告
                logger.warning(f"缓存后端不支持模式删除: {pattern}")
                return 0
        except Exception as e:
            logger.error(f"清除缓存模式失败 {pattern}: {str(e)}")
            return 0
    
    def increment(self, key: str, delta: int = 1) -> int:
        """递增缓存值"""
        try:
            return self.cache.get_or_set(key, 0) + delta
        except Exception as e:
            logger.error(f"递增缓存失败 {key}: {str(e)}")
            return delta
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存"""
        try:
            return self.cache.get_many(keys)
        except Exception as e:
            logger.error(f"批量获取缓存失败: {str(e)}")
            return {}
    
    def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        """批量设置缓存"""
        try:
            timeout = timeout or self.default_timeout
            self.cache.set_many(data, timeout)
            return True
        except Exception as e:
            logger.error(f"批量设置缓存失败: {str(e)}")
            return False


class VideoCacheService(CacheService):
    """视频相关缓存服务"""
    
    def __init__(self):
        super().__init__()
        self.video_timeout = 600  # 10分钟
        self.list_timeout = 300   # 5分钟
        self.stats_timeout = 60   # 1分钟
    
    def get_video_key(self, video_id: int) -> str:
        """生成视频缓存键"""
        return f"video:detail:{video_id}"
    
    def get_video_list_key(self, **filters) -> str:
        """生成视频列表缓存键"""
        # 创建过滤器的哈希值
        filter_str = json.dumps(filters, sort_keys=True)
        filter_hash = hashlib.md5(filter_str.encode()).hexdigest()[:8]
        return f"video:list:{filter_hash}"
    
    def get_video_stats_key(self, video_id: int) -> str:
        """生成视频统计缓存键"""
        return f"video:stats:{video_id}"
    
    def cache_video(self, video_data: Dict[str, Any]) -> bool:
        """缓存视频详情"""
        video_id = video_data.get('id')
        if not video_id:
            return False
        
        key = self.get_video_key(video_id)
        return self.set(key, video_data, self.video_timeout)
    
    def get_cached_video(self, video_id: int) -> Optional[Dict[str, Any]]:
        """获取缓存的视频详情"""
        key = self.get_video_key(video_id)
        return self.get(key)
    
    def cache_video_list(self, videos_data: List[Dict[str, Any]], **filters) -> bool:
        """缓存视频列表"""
        key = self.get_video_list_key(**filters)
        return self.set(key, videos_data, self.list_timeout)
    
    def get_cached_video_list(self, **filters) -> Optional[List[Dict[str, Any]]]:
        """获取缓存的视频列表"""
        key = self.get_video_list_key(**filters)
        return self.get(key)
    
    def invalidate_video_cache(self, video_id: int) -> None:
        """使视频相关缓存失效"""
        # 删除视频详情缓存
        video_key = self.get_video_key(video_id)
        self.delete(video_key)
        
        # 删除视频统计缓存
        stats_key = self.get_video_stats_key(video_id)
        self.delete(stats_key)
        
        # 清除视频列表缓存
        self.clear_pattern("video:list:*")
    
    def cache_video_stats(self, video_id: int, stats: Dict[str, Any]) -> bool:
        """缓存视频统计信息"""
        key = self.get_video_stats_key(video_id)
        return self.set(key, stats, self.stats_timeout)
    
    def get_cached_video_stats(self, video_id: int) -> Optional[Dict[str, Any]]:
        """获取缓存的视频统计信息"""
        key = self.get_video_stats_key(video_id)
        return self.get(key)


class UserCacheService(CacheService):
    """用户相关缓存服务"""
    
    def __init__(self):
        super().__init__()
        self.user_timeout = 900  # 15分钟
        self.session_timeout = 3600  # 1小时
    
    def get_user_key(self, user_id: int) -> str:
        """生成用户缓存键"""
        return f"user:profile:{user_id}"
    
    def get_user_permissions_key(self, user_id: int) -> str:
        """生成用户权限缓存键"""
        return f"user:permissions:{user_id}"
    
    def cache_user_profile(self, user_data: Dict[str, Any]) -> bool:
        """缓存用户资料"""
        user_id = user_data.get('id')
        if not user_id:
            return False
        
        key = self.get_user_key(user_id)
        return self.set(key, user_data, self.user_timeout)
    
    def get_cached_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取缓存的用户资料"""
        key = self.get_user_key(user_id)
        return self.get(key)
    
    def cache_user_permissions(self, user_id: int, permissions: Dict[str, bool]) -> bool:
        """缓存用户权限"""
        key = self.get_user_permissions_key(user_id)
        return self.set(key, permissions, self.user_timeout)
    
    def get_cached_user_permissions(self, user_id: int) -> Optional[Dict[str, bool]]:
        """获取缓存的用户权限"""
        key = self.get_user_permissions_key(user_id)
        return self.get(key)
    
    def invalidate_user_cache(self, user_id: int) -> None:
        """使用户相关缓存失效"""
        user_key = self.get_user_key(user_id)
        permissions_key = self.get_user_permissions_key(user_id)
        
        self.delete(user_key)
        self.delete(permissions_key)


class SystemCacheService(CacheService):
    """系统级缓存服务"""
    
    def __init__(self):
        super().__init__()
        self.system_timeout = 300  # 5分钟
    
    def cache_system_stats(self, stats: Dict[str, Any]) -> bool:
        """缓存系统统计信息"""
        return self.set("system:stats", stats, self.system_timeout)
    
    def get_cached_system_stats(self) -> Optional[Dict[str, Any]]:
        """获取缓存的系统统计信息"""
        return self.get("system:stats")
    
    def cache_storage_info(self, storage_info: Dict[str, Any]) -> bool:
        """缓存存储信息"""
        return self.set("system:storage", storage_info, self.system_timeout)
    
    def get_cached_storage_info(self) -> Optional[Dict[str, Any]]:
        """获取缓存的存储信息"""
        return self.get("system:storage")
    
    def cache_categories(self, categories: List[Dict[str, str]]) -> bool:
        """缓存视频分类列表"""
        return self.set("system:categories", categories, 3600)  # 1小时
    
    def get_cached_categories(self) -> Optional[List[Dict[str, str]]]:
        """获取缓存的视频分类列表"""
        return self.get("system:categories")


# 创建全局缓存服务实例
video_cache = VideoCacheService()
user_cache = UserCacheService()
system_cache = SystemCacheService()


def cache_queryset(queryset: QuerySet, key: str, timeout: int = 300) -> List[Dict]:
    """缓存QuerySet结果"""
    cache_service = CacheService()
    
    def get_data():
        # 将QuerySet序列化为JSON
        serialized = serialize('json', queryset)
        return json.loads(serialized)
    
    return cache_service.get_or_set(key, get_data, timeout)


def invalidate_cache_pattern(pattern: str) -> int:
    """使匹配模式的缓存失效"""
    cache_service = CacheService()
    return cache_service.clear_pattern(pattern)


def warm_up_cache():
    """预热缓存 - 加载常用数据"""
    try:
        from videos.models import Video
        
        # 预热热门视频
        popular_videos = Video.objects.filter(is_active=True).order_by('-view_count')[:10]
        for video in popular_videos:
            video_data = {
                'id': video.id,
                'title': video.title,
                'description': video.description,
                'view_count': video.view_count,
                'category': video.category,
                'upload_time': video.upload_time.isoformat(),
            }
            video_cache.cache_video(video_data)
        
        # 预热分类列表
        from videos.models import Video
        categories = [
            {'value': choice[0], 'label': choice[1]}
            for choice in Video.CATEGORY_CHOICES
        ]
        system_cache.cache_categories(categories)
        
        logger.info("缓存预热完成")
        
    except Exception as e:
        logger.error(f"缓存预热失败: {str(e)}")


def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计信息"""
    try:
        cache_service = CacheService()
        
        # 本地内存缓存统计信息
        return {
            'backend': 'Local Memory Cache',
            'status': 'active',
            'cache_type': 'django.core.cache.backends.locmem.LocMemCache',
            'note': '使用本地内存缓存，重启后数据会丢失'
        }
    
    except Exception as e:
        logger.error(f"获取缓存统计失败: {str(e)}")
        return {
            'backend': 'Unknown',
            'error': str(e)
        }