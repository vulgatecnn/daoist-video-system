# 确保Django启动时加载Celery应用
from .celery import app as celery_app

__all__ = ('celery_app',)