# PDF to Markdown API

这是一个API服务，使用[marker](https://github.com/VikParuchuri/marker)项目的命令行工具将PDF文件转换为Markdown格式。

## 功能特点

- 提供REST API，接收PDF URL作为输入
- 将PDF文件转换为高质量的Markdown格式
- 支持各种PDF格式，包括科学论文、书籍等
- 通过执行marker_single命令行工具实现转换，不预加载模型
- 将转换后的Markdown文件上传到腾讯云COS对象存储
- 自动替换Markdown中的本地图片引用为COS远程URL

## 先决条件

- Python 3.12或更高版本
- marker_single命令可执行（该命令由marker包提供）
- 腾讯云COS账号及相关配置

## 安装

```bash
# 安装项目
python -m pip install uv
uv venv
source .venv/bin/activate  # 在Windows上使用 .venv\Scripts\activate
uv pip install -e .
```

## 配置腾讯云COS

1. 创建一个`.env`文件，参考`.env.example`文件的格式
2. 填入您的腾讯云COS配置信息：
   ```
   COS_SECRET_ID=your_secret_id_here
   COS_SECRET_KEY=your_secret_key_here
   COS_REGION=ap-guangzhou
   COS_BUCKET=your-bucket-name-1250000000
   ```

## 运行服务

```bash
python run.py
```

服务将在 http://localhost:8000 上运行，你可以访问 http://localhost:8000/docs 查看API文档。

## API使用

### 转换PDF到Markdown

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/convert' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "pdf_url": "https://example.com/sample.pdf"
}'
```

### 响应示例

```json
{
  "file_url": "https://your-bucket-1250000000.cos.ap-guangzhou.myqcloud.com/tmp/sample_1628123456/sample.md"
}
```

## 图片URL替换功能

服务现在会自动将Markdown文本中的本地图片引用替换为COS远程URL。例如，原始Markdown中的图片引用：

```markdown
![图片描述](images/example.png)
```

会被替换为：

```markdown
![图片描述](https://your-bucket-1250000000.cos.ap-guangzhou.myqcloud.com/pdf-name_timestamp/images/example.png)
```

这样，即使在外部环境中查看Markdown内容，也能正确显示图片。替换逻辑支持：

1. 完整路径匹配（如`images/example.png`）
2. 文件名匹配（如`example.png`）
3. 智能忽略已经是HTTP/HTTPS URL的图片引用

## 工作原理

1. API服务接收包含PDF URL的请求
2. 下载PDF文件到临时位置，保留原始文件名并添加随机字符串
3. 执行marker_single命令行工具处理PDF文件
4. 读取生成的Markdown内容
5. 上传所有图片等资源文件到COS
6. 替换Markdown中的本地图片引用为COS远程URL
7. 将替换后的Markdown内容上传到COS
8. 返回Markdown文件的COS URL
9. 清理所有临时文件

## 许可证

本项目使用GNU通用公共许可证(GPL-3.0)。请注意，marker项目有自己的许可证要求，商业使用可能需要额外许可。
