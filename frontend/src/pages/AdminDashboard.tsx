/**
 * 管理员仪表板
 * 提供视频管理、批量操作等功能
 */
import React, { useState, useEffect } from 'react';
import { 
  Table, 
  Button, 
  Input, 
  Select, 
  Space, 
  Modal, 
  Form, 
  message, 
  Checkbox, 
  Tag, 
  Tooltip,
  Card,
  Row,
  Col,
  Statistic,
  Popconfirm
} from 'antd';
import { 
  SearchOutlined, 
  EditOutlined, 
  DeleteOutlined, 
  UploadOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { videoService } from '../services/videoService';
import { Video } from '../types';

const { Option } = Select;
const { confirm } = Modal;

interface VideoCategory {
  value: string;
  label: string;
}

const AdminDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [videos, setVideos] = useState<Video[]>([]);
  const [categories, setCategories] = useState<VideoCategory[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [searchText, setSearchText] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<boolean | undefined>(undefined);
  
  // 编辑模态框状态
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingVideo, setEditingVideo] = useState<Video | null>(null);
  const [editForm] = Form.useForm();

  // 统计数据
  const [stats, setStats] = useState({
    totalVideos: 0,
    activeVideos: 0,
    totalViews: 0,
    totalSize: 0
  });

  // 加载视频列表
  const loadVideos = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (searchText) params.search = searchText;
      if (selectedCategory) params.category = selectedCategory;
      if (statusFilter !== undefined) params.is_active = statusFilter;

      const response = await videoService.getAdminVideos(params);
      setVideos(response);
      
      // 计算统计数据
      const totalVideos = response.length;
      const activeVideos = response.filter((v: Video) => v.is_active).length;
      const totalViews = response.reduce((sum: number, v: Video) => sum + v.view_count, 0);
      const totalSize = response.reduce((sum: number, v: Video) => sum + v.file_size, 0);
      
      setStats({
        totalVideos,
        activeVideos,
        totalViews,
        totalSize
      });
    } catch (error) {
      message.error('加载视频列表失败');
      console.error('加载视频列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 加载视频分类
  const loadCategories = async () => {
    try {
      const response = await videoService.getVideoCategories();
      setCategories(response);
    } catch (error) {
      console.error('加载分类失败:', error);
    }
  };

  useEffect(() => {
    loadVideos();
    loadCategories();
  }, [searchText, selectedCategory, statusFilter]);

  // 表格列定义
  const columns = [
    {
      title: '视频信息',
      key: 'info',
      render: (record: Video) => (
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {record.thumbnail && (
            <img 
              src={record.thumbnail} 
              alt={record.title}
              style={{ width: 60, height: 40, objectFit: 'cover', marginRight: 12 }}
            />
          )}
          <div>
            <div style={{ fontWeight: 'bold' }}>{record.title}</div>
            <div style={{ color: '#666', fontSize: '12px' }}>
              {record.description.length > 50 
                ? `${record.description.substring(0, 50)}...` 
                : record.description
              }
            </div>
          </div>
        </div>
      ),
      width: 300,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => <Tag color="blue">{category}</Tag>,
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? '正常' : '已删除'}
        </Tag>
      ),
      width: 80,
    },
    {
      title: '观看次数',
      dataIndex: 'view_count',
      key: 'view_count',
      sorter: (a: Video, b: Video) => a.view_count - b.view_count,
      width: 100,
    },
    {
      title: '文件大小',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => `${(size / 1024 / 1024).toFixed(1)} MB`,
      sorter: (a: Video, b: Video) => a.file_size - b.file_size,
      width: 100,
    },
    {
      title: '上传时间',
      dataIndex: 'upload_time',
      key: 'upload_time',
      render: (time: string) => new Date(time).toLocaleDateString(),
      sorter: (a: Video, b: Video) => new Date(a.upload_time).getTime() - new Date(b.upload_time).getTime(),
      width: 120,
    },
    {
      title: '操作',
      key: 'actions',
      render: (record: Video) => (
        <Space>
          <Tooltip title="编辑">
            <Button 
              type="text" 
              icon={<EditOutlined />} 
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Popconfirm
              title="确定要删除这个视频吗？"
              onConfirm={() => handleDelete([record.id])}
              okText="确定"
              cancelText="取消"
            >
              <Button 
                type="text" 
                danger 
                icon={<DeleteOutlined />}
              />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
      width: 100,
    },
  ];

  // 行选择配置
  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => {
      setSelectedRowKeys(keys as number[]);
    },
    getCheckboxProps: (record: Video) => ({
      disabled: false,
    }),
  };

  // 处理编辑
  const handleEdit = (video: Video) => {
    setEditingVideo(video);
    editForm.setFieldsValue({
      title: video.title,
      description: video.description,
      category: video.category,
    });
    setEditModalVisible(true);
  };

  // 处理编辑提交
  const handleEditSubmit = async () => {
    try {
      const values = await editForm.validateFields();
      if (editingVideo) {
        await videoService.adminUpdateVideo(editingVideo.id, values);
        message.success('视频信息更新成功');
        setEditModalVisible(false);
        setEditingVideo(null);
        loadVideos();
      }
    } catch (error) {
      message.error('更新失败');
      console.error('更新视频失败:', error);
    }
  };

  // 处理删除
  const handleDelete = async (videoIds: number[]) => {
    try {
      await videoService.batchDeleteVideos(videoIds);
      message.success(`成功删除 ${videoIds.length} 个视频`);
      setSelectedRowKeys([]);
      loadVideos();
    } catch (error) {
      message.error('删除失败');
      console.error('删除视频失败:', error);
    }
  };

  // 处理批量分类更新
  const handleBatchCategoryUpdate = (category: string) => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要更新的视频');
      return;
    }

    confirm({
      title: '批量更新分类',
      icon: <ExclamationCircleOutlined />,
      content: `确定要将选中的 ${selectedRowKeys.length} 个视频的分类更新为 "${category}" 吗？`,
      onOk: async () => {
        try {
          await videoService.batchUpdateCategory(selectedRowKeys, category);
          message.success(`成功更新 ${selectedRowKeys.length} 个视频的分类`);
          setSelectedRowKeys([]);
          loadVideos();
        } catch (error) {
          message.error('批量更新失败');
          console.error('批量更新分类失败:', error);
        }
      },
    });
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div style={{ padding: '24px' }}>
      <h1>视频管理</h1>
      
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="总视频数" value={stats.totalVideos} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="正常视频" value={stats.activeVideos} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="总观看次数" value={stats.totalViews} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="总存储大小" 
              value={formatFileSize(stats.totalSize)} 
            />
          </Card>
        </Col>
      </Row>

      {/* 操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space>
              <Input
                placeholder="搜索视频标题或描述"
                prefix={<SearchOutlined />}
                value={searchText}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchText(e.target.value)}
                style={{ width: 250 }}
              />
              <Select
                placeholder="选择分类"
                value={selectedCategory}
                onChange={setSelectedCategory}
                allowClear
                style={{ width: 150 }}
              >
                {categories.map(cat => (
                  <Option key={cat.value} value={cat.value}>{cat.label}</Option>
                ))}
              </Select>
              <Select
                placeholder="状态筛选"
                value={statusFilter}
                onChange={setStatusFilter}
                allowClear
                style={{ width: 120 }}
              >
                <Option value={true}>正常</Option>
                <Option value={false}>已删除</Option>
              </Select>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={loadVideos}
              >
                刷新
              </Button>
            </Space>
          </Col>
          <Col>
            <Button 
              type="primary" 
              icon={<UploadOutlined />}
              onClick={() => navigate('/admin/upload')}
            >
              上传视频
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 批量操作栏 */}
      {selectedRowKeys.length > 0 && (
        <Card style={{ marginBottom: 16, backgroundColor: '#f6ffed' }}>
          <Space>
            <span>已选择 {selectedRowKeys.length} 个视频</span>
            <Popconfirm
              title={`确定要删除选中的 ${selectedRowKeys.length} 个视频吗？`}
              onConfirm={() => handleDelete(selectedRowKeys)}
              okText="确定"
              cancelText="取消"
            >
              <Button danger icon={<DeleteOutlined />}>
                批量删除
              </Button>
            </Popconfirm>
            <span>批量更新分类：</span>
            {categories.map(cat => (
              <Button 
                key={cat.value}
                size="small"
                onClick={() => handleBatchCategoryUpdate(cat.value)}
              >
                {cat.label}
              </Button>
            ))}
          </Space>
        </Card>
      )}

      {/* 视频列表表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={videos}
          rowKey="id"
          rowSelection={rowSelection}
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total: number, range: [number, number]) => 
              `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>

      {/* 编辑模态框 */}
      <Modal
        title="编辑视频信息"
        open={editModalVisible}
        onOk={handleEditSubmit}
        onCancel={() => {
          setEditModalVisible(false);
          setEditingVideo(null);
        }}
        okText="保存"
        cancelText="取消"
      >
        <Form form={editForm} layout="vertical">
          <Form.Item
            name="title"
            label="视频标题"
            rules={[{ required: true, message: '请输入视频标题' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="description"
            label="视频描述"
            rules={[{ required: true, message: '请输入视频描述' }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item
            name="category"
            label="视频分类"
            rules={[{ required: true, message: '请选择视频分类' }]}
          >
            <Select>
              {categories.map(cat => (
                <Option key={cat.value} value={cat.value}>{cat.label}</Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdminDashboard;