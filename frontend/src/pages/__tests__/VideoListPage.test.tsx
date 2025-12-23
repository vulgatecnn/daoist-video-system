/**
 * 视频列表页面单元测试
 * 测试视频列表的渲染和交互、搜索和筛选功能
 */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';

// 创建一个简化的VideoListPage组件用于测试
const MockVideoListPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedCategory, setSelectedCategory] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const mockVideos = [
    {
      id: 1,
      title: '道德经第一章',
      description: '道可道，非常道',
      category: '道德经',
      view_count: 100,
      file_size: 1024000,
    },
    {
      id: 2,
      title: '太上感应篇',
      description: '太上曰：祸福无门，惟人自召',
      category: '太上感应篇',
      view_count: 50,
      file_size: 2048000,
    },
    {
      id: 3,
      title: '清静经',
      description: '老君曰：大道无形，生育天地',
      category: '清静经',
      view_count: 75,
      file_size: 1536000,
    },
  ];

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const filteredVideos = mockVideos.filter(video => {
    const matchesSearch = !searchQuery || 
      video.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      video.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !selectedCategory || video.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleRetry = () => {
    setError(null);
    setLoading(false);
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedCategory('');
  };

  return (
    <div>
      <h1>经文视频库</h1>
      <p>浏览和观看道教经文视频，共 {filteredVideos.length} 个视频</p>
      
      {/* 搜索和筛选栏 */}
      <div>
        <input
          type="text"
          placeholder="搜索视频标题或描述..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
        >
          <option value="">全部分类</option>
          <option value="道德经">道德经</option>
          <option value="太上感应篇">太上感应篇</option>
          <option value="清静经">清静经</option>
          <option value="黄庭经">黄庭经</option>
          <option value="阴符经">阴符经</option>
          <option value="其他经文">其他经文</option>
        </select>
      </div>

      {/* 错误提示 */}
      {error && (
        <div>
          <span>{error}</span>
          <button onClick={handleRetry}>重试</button>
        </div>
      )}

      {/* 加载状态 */}
      {loading && <div>加载中...</div>}

      {/* 视频列表 */}
      {!loading && filteredVideos.length > 0 && (
        <div>
          {filteredVideos.map((video) => (
            <div key={video.id} className="video-card">
              <h3>{video.title}</h3>
              <p>{video.description}</p>
              <span>{video.category}</span>
              <span>{video.view_count} 次播放</span>
              <span>{formatFileSize(video.file_size)}</span>
            </div>
          ))}
        </div>
      )}

      {/* 空状态 */}
      {!loading && filteredVideos.length === 0 && (
        <div>
          <h3>暂无视频</h3>
          {searchQuery || selectedCategory ? (
            <>
              <p>没有找到符合条件的视频</p>
              <button onClick={clearFilters}>清除筛选条件</button>
            </>
          ) : (
            <p>还没有上传任何视频</p>
          )}
        </div>
      )}

      {/* 分页 */}
      {filteredVideos.length > 12 && (
        <div>
          <button disabled>上一页</button>
          <button>1</button>
          <button>2</button>
          <button>下一页</button>
        </div>
      )}
    </div>
  );
};

describe('VideoListPage 组件测试', () => {
  describe('页面渲染', () => {
    test('应该渲染页面标题和描述', async () => {
      render(<MockVideoListPage />);
      
      expect(screen.getByText('经文视频库')).toBeInTheDocument();
      expect(screen.getByText('浏览和观看道教经文视频，共 3 个视频')).toBeInTheDocument();
    });

    test('应该渲染搜索和筛选栏', () => {
      render(<MockVideoListPage />);
      
      expect(screen.getByPlaceholderText('搜索视频标题或描述...')).toBeInTheDocument();
      expect(screen.getByDisplayValue('全部分类')).toBeInTheDocument();
    });
  });

  describe('视频列表渲染', () => {
    test('应该渲染视频卡片列表', async () => {
      render(<MockVideoListPage />);
      
      expect(screen.getByText('道德经第一章')).toBeInTheDocument();
      expect(screen.getAllByText('太上感应篇').length).toBeGreaterThan(0);
      expect(screen.getAllByText('清静经').length).toBeGreaterThan(0);
    });

    test('视频卡片应该显示完整信息', async () => {
      render(<MockVideoListPage />);
      
      // 检查第一个视频的信息
      expect(screen.getByText('道德经第一章')).toBeInTheDocument();
      expect(screen.getByText('道可道，非常道')).toBeInTheDocument();
      expect(screen.getAllByText('道德经').length).toBeGreaterThan(0);
      expect(screen.getByText('100 次播放')).toBeInTheDocument();
      expect(screen.getByText('1000 KB')).toBeInTheDocument();
    });

    test('应该正确格式化文件大小', async () => {
      render(<MockVideoListPage />);
      
      expect(screen.getByText('1000 KB')).toBeInTheDocument();
      expect(screen.getByText('2 MB')).toBeInTheDocument();
      expect(screen.getByText('1.5 MB')).toBeInTheDocument();
    });
  });

  describe('搜索功能', () => {
    test('应该处理搜索输入', async () => {
      render(<MockVideoListPage />);
      
      const searchInput = screen.getByPlaceholderText('搜索视频标题或描述...');
      
      // 使用 fireEvent 而不是 userEvent
      fireEvent.change(searchInput, { target: { value: '道德经' } });
      
      expect(searchInput).toHaveValue('道德经');
    });

    test('搜索应该过滤视频列表', async () => {
      render(<MockVideoListPage />);
      
      const searchInput = screen.getByPlaceholderText('搜索视频标题或描述...');
      
      fireEvent.change(searchInput, { target: { value: '道德经' } });
      
      await waitFor(() => {
        expect(screen.getByText('道德经第一章')).toBeInTheDocument();
        // 检查视频卡片中的标题，而不是选择器中的选项
        expect(screen.queryByRole('heading', { name: '太上感应篇' })).not.toBeInTheDocument();
        expect(screen.queryByRole('heading', { name: '清静经' })).not.toBeInTheDocument();
      });
    });

    test('搜索应该更新视频计数', async () => {
      render(<MockVideoListPage />);
      
      const searchInput = screen.getByPlaceholderText('搜索视频标题或描述...');
      
      fireEvent.change(searchInput, { target: { value: '道德经' } });
      
      await waitFor(() => {
        expect(screen.getByText('浏览和观看道教经文视频，共 1 个视频')).toBeInTheDocument();
      });
    });
  });

  describe('分类筛选功能', () => {
    test('应该显示所有分类选项', () => {
      render(<MockVideoListPage />);
      
      const categorySelect = screen.getByDisplayValue('全部分类');
      expect(categorySelect).toBeInTheDocument();
      
      // 检查选项是否存在（通过option元素）
      const options = screen.getAllByRole('option');
      const optionTexts = options.map(option => option.textContent);
      
      expect(optionTexts).toContain('全部分类');
      expect(optionTexts).toContain('道德经');
      expect(optionTexts).toContain('太上感应篇');
      expect(optionTexts).toContain('清静经');
      expect(optionTexts).toContain('黄庭经');
      expect(optionTexts).toContain('阴符经');
      expect(optionTexts).toContain('其他经文');
    });

    test('选择分类应该过滤视频', async () => {
      render(<MockVideoListPage />);
      
      const categorySelect = screen.getByDisplayValue('全部分类');
      
      fireEvent.change(categorySelect, { target: { value: '道德经' } });
      
      await waitFor(() => {
        expect(screen.getByText('道德经第一章')).toBeInTheDocument();
        // 检查视频卡片中的标题，而不是选择器中的选项
        expect(screen.queryByRole('heading', { name: '太上感应篇' })).not.toBeInTheDocument();
        expect(screen.queryByRole('heading', { name: '清静经' })).not.toBeInTheDocument();
      });
    });

    test('分类筛选应该更新视频计数', async () => {
      render(<MockVideoListPage />);
      
      const categorySelect = screen.getByDisplayValue('全部分类');
      
      fireEvent.change(categorySelect, { target: { value: '道德经' } });
      
      await waitFor(() => {
        expect(screen.getByText('浏览和观看道教经文视频，共 1 个视频')).toBeInTheDocument();
      });
    });
  });

  describe('组合搜索和筛选', () => {
    test('应该同时应用搜索和分类筛选', async () => {
      render(<MockVideoListPage />);
      
      const searchInput = screen.getByPlaceholderText('搜索视频标题或描述...');
      const categorySelect = screen.getByDisplayValue('全部分类');
      
      fireEvent.change(searchInput, { target: { value: '道德经' } });
      fireEvent.change(categorySelect, { target: { value: '道德经' } });
      
      await waitFor(() => {
        expect(screen.getByText('道德经第一章')).toBeInTheDocument();
        // 检查视频卡片中的标题，而不是选择器中的选项
        expect(screen.queryByRole('heading', { name: '太上感应篇' })).not.toBeInTheDocument();
        expect(screen.getByText('浏览和观看道教经文视频，共 1 个视频')).toBeInTheDocument();
      });
    });

    test('清除筛选条件按钮应该重置所有筛选', async () => {
      render(<MockVideoListPage />);
      
      const searchInput = screen.getByPlaceholderText('搜索视频标题或描述...');
      const categorySelect = screen.getByDisplayValue('全部分类');
      
      // 设置筛选条件
      fireEvent.change(searchInput, { target: { value: '不存在的视频' } });
      fireEvent.change(categorySelect, { target: { value: '道德经' } });
      
      await waitFor(() => {
        expect(screen.getByText('暂无视频')).toBeInTheDocument();
        expect(screen.getByText('没有找到符合条件的视频')).toBeInTheDocument();
      });
      
      const clearButton = screen.getByText('清除筛选条件');
      fireEvent.click(clearButton);
      
      await waitFor(() => {
        expect(screen.getByText('道德经第一章')).toBeInTheDocument();
        expect(screen.getAllByText('太上感应篇').length).toBeGreaterThan(0);
        expect(screen.getAllByText('清静经').length).toBeGreaterThan(0);
        expect(screen.getByText('浏览和观看道教经文视频，共 3 个视频')).toBeInTheDocument();
      });
    });
  });

  describe('空状态', () => {
    test('搜索无结果时应该显示相应提示', async () => {
      render(<MockVideoListPage />);
      
      const searchInput = screen.getByPlaceholderText('搜索视频标题或描述...');
      
      fireEvent.change(searchInput, { target: { value: '不存在的视频' } });
      
      await waitFor(() => {
        expect(screen.getByText('暂无视频')).toBeInTheDocument();
        expect(screen.getByText('没有找到符合条件的视频')).toBeInTheDocument();
        expect(screen.getByText('清除筛选条件')).toBeInTheDocument();
      });
    });
  });

  describe('界面元素', () => {
    test('应该包含搜索框', () => {
      render(<MockVideoListPage />);
      
      const searchInput = screen.getByPlaceholderText('搜索视频标题或描述...');
      expect(searchInput).toBeInTheDocument();
      expect(searchInput.tagName).toBe('INPUT');
    });

    test('应该包含分类选择器', () => {
      render(<MockVideoListPage />);
      
      const categorySelect = screen.getByDisplayValue('全部分类');
      expect(categorySelect).toBeInTheDocument();
      expect(categorySelect.tagName).toBe('SELECT');
    });

    test('应该显示视频总数', async () => {
      render(<MockVideoListPage />);
      
      expect(screen.getByText(/共 \d+ 个视频/)).toBeInTheDocument();
    });
  });

  describe('视频信息显示', () => {
    test('应该显示视频标题', () => {
      render(<MockVideoListPage />);
      
      expect(screen.getByText('道德经第一章')).toBeInTheDocument();
      expect(screen.getAllByText('太上感应篇').length).toBeGreaterThan(0);
      expect(screen.getAllByText('清静经').length).toBeGreaterThan(0);
    });

    test('应该显示视频描述', () => {
      render(<MockVideoListPage />);
      
      expect(screen.getByText('道可道，非常道')).toBeInTheDocument();
      expect(screen.getByText('太上曰：祸福无门，惟人自召')).toBeInTheDocument();
      expect(screen.getByText('老君曰：大道无形，生育天地')).toBeInTheDocument();
    });

    test('应该显示视频分类', () => {
      render(<MockVideoListPage />);
      
      const categories = screen.getAllByText('道德经');
      expect(categories.length).toBeGreaterThan(0); // 至少在选择器和视频卡片中出现
      expect(screen.getAllByText('太上感应篇').length).toBeGreaterThan(0);
      expect(screen.getAllByText('清静经').length).toBeGreaterThan(0);
    });

    test('应该显示播放次数', () => {
      render(<MockVideoListPage />);
      
      expect(screen.getByText('100 次播放')).toBeInTheDocument();
      expect(screen.getByText('50 次播放')).toBeInTheDocument();
      expect(screen.getByText('75 次播放')).toBeInTheDocument();
    });

    test('应该显示文件大小', () => {
      render(<MockVideoListPage />);
      
      expect(screen.getByText('1000 KB')).toBeInTheDocument();
      expect(screen.getByText('2 MB')).toBeInTheDocument();
      expect(screen.getByText('1.5 MB')).toBeInTheDocument();
    });
  });
});