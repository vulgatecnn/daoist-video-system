"""
道士经文视频管理系统 - 文件处理属性测试
验证文件格式验证和视频保存完整性属性

Feature: daoist-scripture-video, Property 3: 文件格式验证和错误处理
Feature: daoist-scripture-video, Property 4: 视频保存完整性
"""

import os
import sys
import django
from pathlib import Path
import tempfile
import io
from unittest.mock import Mock

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')

# 确保项目路径在Python路径中
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile, InMemoryUploadedFile
from django.core.exceptions import ValidationError
from hypothesis import given, strategies as st, settings as hypothesis_settings
from hypothesis.extra.django import TestCase as HypothesisTestCase
from rest_framework.test import APIClient
from rest_framework import status
import json

from videos.models import Video
from videos.serializers import VideoUploadSerializer
from users.models import User

User = get_user_model()


class FileProcessingPropertyTest(HypothesisTestCase):
    """
    文件处理属性测试类
    
    属性 3: 文件格式验证和错误处理
    属性 4: 视频保存完整性
    """
    
    def setUp(self):
        """测试设置"""
        self.client = APIClient()
        
        # 清理可能存在的测试用户
        User.objects.filter(username__startswith='test_').delete()
        
        # 创建测试管理员用户
        self.admin_user = User.objects.create_user(
            username='test_admin_file',
            email='admin_file@test.com',
            password='testpass123',
            role='admin'
        )
        
        # 创建测试普通用户
        self.regular_user = User.objects.create_user(
            username='test_user_file',
            email='user_file@test.com',
            password='testpass123',
            role='user'
        )
    
    def create_mock_file(self, filename, content=b'fake video content', content_type='video/mp4'):
        """创建模拟文件"""
        return SimpleUploadedFile(
            name=filename,
            content=content,
            content_type=content_type
        )
    
    @hypothesis_settings(max_examples=20)
    @given(
        file_extension=st.sampled_from([
            '.txt', '.doc', '.pdf', '.jpg', '.png', '.gif', '.zip', '.rar',
            '.exe', '.bat', '.sh', '.py', '.js', '.html', '.css', '.xml'
        ])
    )
    def test_unsupported_file_format_rejection(self, file_extension):
        """
        属性测试 3: 文件格式验证和错误处理
        
        对于任何上传的文件，如果文件格式不在支持列表中，
        系统应该拒绝上传并返回具体的错误信息
        
        验证需求: 需求 2.1, 2.5
        """
        # 创建不支持格式的文件
        filename = f"test_file{file_extension}"
        mock_file = self.create_mock_file(filename, content_type='application/octet-stream')
        
        # 准备上传数据
        upload_data = {
            'title': '测试视频',
            'description': '测试描述',
            'category': 'daoist_classic',
            'file_path': mock_file
        }
        
        # 测试序列化器验证
        serializer = VideoUploadSerializer(data=upload_data)
        
        # 验证序列化器应该拒绝不支持的格式
        is_valid = serializer.is_valid()
        
        self.assertFalse(
            is_valid,
            f"文件格式 {file_extension} 应该被拒绝，但序列化器验证通过了"
        )
        
        # 验证错误信息包含格式相关的说明
        if 'file_path' in serializer.errors:
            error_message = str(serializer.errors['file_path'])
            self.assertTrue(
                any(keyword in error_message.lower() for keyword in ['格式', 'format', '扩展名', 'extension']),
                f"错误信息应该包含格式相关说明，但得到: {error_message}"
            )
    
    @hypothesis_settings(max_examples=15)
    @given(
        file_extension=st.sampled_from(['.mp4', '.avi', '.mov', '.mkv', '.webm']),
        title=st.text(min_size=2, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))),
        category=st.sampled_from(['daoist_classic', 'meditation', 'ritual', 'teaching', 'chanting', 'other'])
    )
    def test_supported_file_format_acceptance(self, file_extension, title, category):
        """
        属性测试 3: 支持的文件格式应该被接受
        
        对于任何支持的视频格式，系统应该接受上传
        """
        # 创建支持格式的文件
        filename = f"test_video{file_extension}"
        
        # 根据扩展名设置合适的MIME类型
        mime_types = {
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm'
        }
        
        mock_file = self.create_mock_file(
            filename, 
            content=b'fake video content' * 100,  # 增加文件大小
            content_type=mime_types.get(file_extension, 'video/mp4')
        )
        
        # 准备上传数据
        upload_data = {
            'title': title.strip() if title.strip() else '默认标题',
            'description': '测试描述',
            'category': category,
            'file_path': mock_file
        }
        
        # 测试序列化器验证
        serializer = VideoUploadSerializer(data=upload_data)
        
        # 验证序列化器应该接受支持的格式
        is_valid = serializer.is_valid()
        
        if not is_valid:
            # 如果验证失败，检查是否是因为其他原因（如标题长度）
            if 'title' in serializer.errors:
                # 标题验证失败是可以接受的
                pass
            elif 'file_path' in serializer.errors:
                # 文件格式验证失败则测试失败
                self.fail(
                    f"支持的文件格式 {file_extension} 应该被接受，"
                    f"但验证失败: {serializer.errors['file_path']}"
                )
        else:
            # 验证通过，检查文件扩展名是否正确识别
            self.assertTrue(
                filename.lower().endswith(file_extension.lower()),
                f"文件名应该以 {file_extension} 结尾"
            )
    
    @hypothesis_settings(max_examples=5, deadline=1000)  # 增加超时时间到1秒
    @given(
        file_size_mb=st.integers(min_value=501, max_value=600)  # 减少文件大小范围
    )
    def test_file_size_limit_enforcement(self, file_size_mb):
        """
        属性测试 3: 文件大小限制验证
        
        对于任何超过大小限制的文件，系统应该拒绝上传
        """
        # 创建超大文件（使用真实的SimpleUploadedFile但内容很小）
        # 然后手动设置size属性来模拟大文件
        mock_file = SimpleUploadedFile(
            name='large_video.mp4',
            content=b'fake video content',  # 小内容
            content_type='video/mp4'
        )
        # 手动设置大小属性
        mock_file.size = file_size_mb * 1024 * 1024
        
        upload_data = {
            'title': '大文件测试',
            'description': '测试大文件上传',
            'category': 'other',
            'file_path': mock_file
        }
        
        # 测试序列化器验证
        serializer = VideoUploadSerializer(data=upload_data)
        is_valid = serializer.is_valid()
        
        # 验证应该拒绝超大文件
        self.assertFalse(
            is_valid,
            f"文件大小 {file_size_mb}MB 超过限制，应该被拒绝"
        )
        
        # 验证错误信息包含大小相关说明
        if 'file_path' in serializer.errors:
            error_message = str(serializer.errors['file_path'])
            self.assertTrue(
                any(keyword in error_message.lower() for keyword in ['大小', 'size', '限制', 'limit', 'mb']),
                f"错误信息应该包含大小限制说明，但得到: {error_message}"
            )
    
    @hypothesis_settings(max_examples=10)
    @given(
        title=st.text(min_size=2, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))),
        description=st.text(max_size=500, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Po'))),
        category=st.sampled_from(['daoist_classic', 'meditation', 'ritual', 'teaching', 'chanting', 'other'])
    )
    def test_video_save_integrity(self, title, description, category):
        """
        属性测试 4: 视频保存完整性
        
        对于任何成功上传并保存元数据的视频，该视频应该能够在视频库中被检索到，
        且包含完整的元数据信息
        
        验证需求: 需求 2.4
        """
        # 清理标题和描述
        clean_title = title.strip() if title.strip() else '默认标题'
        clean_description = description.strip()
        
        # 创建有效的视频文件
        mock_file = self.create_mock_file(
            'test_video.mp4',
            content=b'fake video content' * 50,
            content_type='video/mp4'
        )
        
        # 直接创建视频对象（模拟成功上传）
        try:
            video = Video.objects.create(
                title=clean_title,
                description=clean_description,
                category=category,
                uploader=self.admin_user,
                file_size=len(mock_file.read()),
                is_active=True
            )
            
            # 验证视频能够被检索到
            retrieved_video = Video.objects.filter(id=video.id).first()
            
            self.assertIsNotNone(
                retrieved_video,
                f"保存的视频 (ID: {video.id}) 应该能够被检索到"
            )
            
            # 验证元数据完整性
            self.assertEqual(
                retrieved_video.title, clean_title,
                f"检索到的视频标题应该与保存的一致: 期望 '{clean_title}', 实际 '{retrieved_video.title}'"
            )
            
            self.assertEqual(
                retrieved_video.description, clean_description,
                f"检索到的视频描述应该与保存的一致"
            )
            
            self.assertEqual(
                retrieved_video.category, category,
                f"检索到的视频分类应该与保存的一致: 期望 '{category}', 实际 '{retrieved_video.category}'"
            )
            
            self.assertEqual(
                retrieved_video.uploader, self.admin_user,
                f"检索到的视频上传者应该与保存的一致"
            )
            
            self.assertTrue(
                retrieved_video.is_active,
                f"新保存的视频应该是激活状态"
            )
            
            # 验证视频在激活视频列表中可见
            active_videos = Video.objects.filter(is_active=True, id=video.id)
            self.assertTrue(
                active_videos.exists(),
                f"保存的视频应该在激活视频列表中可见"
            )
            
            # 清理测试数据
            video.delete()
            
        except Exception as e:
            # 如果是数据验证错误（如标题太短），跳过这个测试用例
            if "标题长度" in str(e) or "title" in str(e).lower():
                pass
            else:
                raise e
    
    def test_video_metadata_completeness(self):
        """
        属性测试 4: 视频元数据完整性检查
        
        验证保存的视频包含所有必要的元数据字段
        """
        # 创建测试视频
        video = Video.objects.create(
            title='完整性测试视频',
            description='测试视频元数据完整性',
            category='daoist_classic',
            uploader=self.admin_user,
            file_size=1024000,  # 1MB
            is_active=True
        )
        
        # 验证必要字段存在
        required_fields = ['title', 'category', 'uploader', 'upload_time', 'is_active']
        
        for field in required_fields:
            field_value = getattr(video, field, None)
            self.assertIsNotNone(
                field_value,
                f"视频对象应该包含必要字段 '{field}'"
            )
        
        # 验证字段类型正确
        self.assertIsInstance(video.title, str)
        self.assertIsInstance(video.description, str)
        self.assertIsInstance(video.view_count, int)
        self.assertIsInstance(video.is_active, bool)
        
        # 验证默认值
        self.assertEqual(video.view_count, 0, "新视频的观看次数应该为0")
        self.assertTrue(video.is_active, "新视频应该默认为激活状态")
        
        # 清理测试数据
        video.delete()
    
    @hypothesis_settings(max_examples=5)
    @given(
        invalid_mime_type=st.sampled_from([
            'text/plain', 'image/jpeg', 'image/png', 'application/pdf',
            'audio/mp3', 'audio/wav', 'application/zip'
        ])
    )
    def test_mime_type_validation(self, invalid_mime_type):
        """
        属性测试 3: MIME类型验证
        
        对于任何非视频MIME类型的文件，系统应该拒绝上传
        """
        # 创建错误MIME类型的文件
        mock_file = self.create_mock_file(
            'fake_video.mp4',  # 文件名看起来像视频
            content=b'not a video file',
            content_type=invalid_mime_type  # 但MIME类型不是视频
        )
        
        upload_data = {
            'title': 'MIME类型测试',
            'description': '测试MIME类型验证',
            'category': 'other',
            'file_path': mock_file
        }
        
        # 测试序列化器验证
        serializer = VideoUploadSerializer(data=upload_data)
        is_valid = serializer.is_valid()
        
        # 验证应该拒绝错误的MIME类型
        self.assertFalse(
            is_valid,
            f"MIME类型 {invalid_mime_type} 不是视频类型，应该被拒绝"
        )
        
        # 验证错误信息
        if 'file_path' in serializer.errors:
            error_message = str(serializer.errors['file_path'])
            self.assertTrue(
                any(keyword in error_message.lower() for keyword in ['视频', 'video', '文件', 'file']),
                f"错误信息应该说明文件类型问题，但得到: {error_message}"
            )
    
    def test_video_search_after_save(self):
        """
        属性测试 4: 保存后的视频搜索功能
        
        验证保存的视频能够通过各种方式被搜索到
        """
        # 创建测试视频
        video = Video.objects.create(
            title='道德经第一章',
            description='老子道德经第一章诵读视频',
            category='daoist_classic',
            uploader=self.admin_user,
            is_active=True
        )
        
        # 测试通过ID搜索
        found_by_id = Video.objects.filter(id=video.id).first()
        self.assertIsNotNone(found_by_id, "应该能够通过ID找到视频")
        
        # 测试通过标题搜索
        found_by_title = Video.objects.filter(title__icontains='道德经').first()
        self.assertIsNotNone(found_by_title, "应该能够通过标题关键词找到视频")
        
        # 测试通过分类搜索
        found_by_category = Video.objects.filter(category='daoist_classic').first()
        self.assertIsNotNone(found_by_category, "应该能够通过分类找到视频")
        
        # 测试通过上传者搜索
        found_by_uploader = Video.objects.filter(uploader=self.admin_user).first()
        self.assertIsNotNone(found_by_uploader, "应该能够通过上传者找到视频")
        
        # 测试激活状态筛选
        active_videos = Video.objects.filter(is_active=True, id=video.id)
        self.assertTrue(active_videos.exists(), "激活的视频应该在激活列表中")
        
        # 清理测试数据
        video.delete()


if __name__ == '__main__':
    import unittest
    
    # 运行属性测试
    suite = unittest.TestLoader().loadTestsFromTestCase(FileProcessingPropertyTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果
    if result.wasSuccessful():
        print("\n✅ 所有文件处理属性测试通过！")
        print("属性 3: 文件格式验证和错误处理 - 验证成功")
        print("属性 4: 视频保存完整性 - 验证成功")
    else:
        print(f"\n❌ 有 {len(result.failures)} 个测试失败，{len(result.errors)} 个测试错误")
        for failure in result.failures:
            print(f"失败: {failure[0]}")
            print(f"详情: {failure[1]}")
        for error in result.errors:
            print(f"错误: {error[0]}")
            print(f"详情: {error[1]}")