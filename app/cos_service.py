import os
import uuid
import time
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from typing import Optional, List, Dict
from dotenv import load_dotenv


class COSService:
    """腾讯云对象存储服务"""

    def __init__(self):
        """初始化COS服务"""
        # 从环境变量获取腾讯云配置
        load_dotenv()
        self.secret_id = os.environ.get('COS_SECRET_ID')
        self.secret_key = os.environ.get('COS_SECRET_KEY')
        self.region = os.environ.get('COS_REGION', 'ap-guangzhou')  # 默认区域
        self.bucket = os.environ.get('COS_BUCKET')
        self.domain = os.environ.get('COS_DOMAIN')  # 可选，自定义域名

        # 确保必要的配置信息存在
        if not self.secret_id or not self.secret_key or not self.bucket:
            print("警告: 腾讯云COS配置不完整，上传功能将不可用")
        else:
            # 创建COS配置和客户端
            self.config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key
            )
            self.client = CosS3Client(self.config)
            print(f"COS服务初始化完成，区域: {self.region}, 存储桶: {self.bucket}")

    def upload_file(self, file_path: str, object_key: Optional[str] = None) -> Optional[str]:
        """
        上传文件到腾讯云COS

        Args:
            file_path: 本地文件路径
            object_key: COS对象键名，如果为None则生成随机名称

        Returns:
            上传成功返回文件的访问URL，失败返回None
        """
        # 检查配置是否完整
        if not self.secret_id or not self.secret_key or not self.bucket:
            print("错误: 腾讯云COS配置不完整，无法上传文件")
            return None

        # 如果未指定对象键名，生成随机UUID作为文件名
        if not object_key:
            file_ext = os.path.splitext(file_path)[1]  # 获取文件扩展名
            object_key = f"{uuid.uuid4()}{file_ext}"

        try:
            # 上传文件
            print(f"开始上传文件到COS: {file_path} -> {object_key}")
            self.client.upload_file(
                Bucket=self.bucket,
                LocalFilePath=file_path,
                Key=object_key,
                EnableMD5=True
            )
            
            # 构建文件访问URL
            if self.domain:
                # 使用自定义域名
                url = f"{self.domain}/{object_key}"
            else:
                # 使用默认COS域名
                url = f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{object_key}"
            
            print(f"文件上传成功: {url}")
            return url
        except Exception as e:
            print(f"文件上传失败: {str(e)}")
            return None

    def upload_content(self, content: str, object_key: Optional[str] = None) -> Optional[str]:
        """
        上传文本内容到腾讯云COS

        Args:
            content: 要上传的文本内容
            object_key: COS对象键名，如果为None则生成随机名称

        Returns:
            上传成功返回文件的访问URL，失败返回None
        """
        # 检查配置是否完整
        if not self.secret_id or not self.secret_key or not self.bucket:
            print("错误: 腾讯云COS配置不完整，无法上传内容")
            return None

        # 如果未指定对象键名，生成随机UUID作为文件名
        if not object_key:
            object_key = f"{uuid.uuid4()}.md"  # 默认使用.md扩展名

        try:
            # 上传文本内容
            print(f"开始上传文本内容到COS: {object_key}")
            response = self.client.put_object(
                Bucket=self.bucket,
                Body=content.encode('utf-8'),
                Key=object_key,
                ContentType='text/markdown'
            )
            
            # 构建文件访问URL
            if self.domain:
                # 使用自定义域名
                url = f"{self.domain}/{object_key}"
            else:
                # 使用默认COS域名
                url = f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{object_key}"
            
            print(f"内容上传成功: {url}")
            return url
        except Exception as e:
            print(f"内容上传失败: {str(e)}")
            return None
            
    def upload_directory(self, local_dir: str, cos_base_path: str) -> Dict[str, str]:
        """
        上传整个目录到腾讯云COS，保持相同的目录结构
        
        Args:
            local_dir: 本地目录路径
            cos_base_path: COS上的基础路径
            
        Returns:
            包含所有上传文件URL的字典，键为相对路径，值为URL
        """
        # 检查配置是否完整
        if not self.secret_id or not self.secret_key or not self.bucket:
            print("错误: 腾讯云COS配置不完整，无法上传目录")
            return {}
            
        if not os.path.isdir(local_dir):
            print(f"错误: {local_dir} 不是有效的目录")
            return {}
            
        # 确保COS路径末尾有斜杠，但不以斜杠开头
        if cos_base_path.startswith('/'):
            cos_base_path = cos_base_path[1:]
        if not cos_base_path.endswith('/') and cos_base_path:
            cos_base_path = f"{cos_base_path}/"
            
        uploaded_files = {}
        
        try:
            print(f"开始上传目录到COS: {local_dir} -> {cos_base_path}")
            
            # 遍历目录中的所有文件
            for root, dirs, files in os.walk(local_dir):
                for file in files:
                    # 构建本地文件完整路径
                    local_file_path = os.path.join(root, file)
                    
                    # 计算相对路径
                    rel_path = os.path.relpath(local_file_path, local_dir)
                    # 将Windows路径分隔符替换为正斜杠
                    rel_path = rel_path.replace('\\', '/')
                    
                    # 构建COS对象键
                    object_key = f"{cos_base_path}{rel_path}"
                    
                    # 获取文件MIME类型
                    content_type = self._get_content_type(file)
                    
                    # 上传文件
                    print(f"上传文件: {local_file_path} -> {object_key}")
                    self.client.upload_file(
                        Bucket=self.bucket,
                        LocalFilePath=local_file_path,
                        Key=object_key,
                        EnableMD5=True,
                        ContentType=content_type
                    )
                    
                    # 构建文件访问URL
                    if self.domain:
                        # 使用自定义域名
                        url = f"{self.domain}/{object_key}"
                    else:
                        # 使用默认COS域名
                        url = f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{object_key}"
                        
                    uploaded_files[rel_path] = url
                    print(f"文件上传成功: {url}")
            
            print(f"目录上传完成，共上传 {len(uploaded_files)} 个文件")
            return uploaded_files
        except Exception as e:
            print(f"上传目录时发生错误: {str(e)}")
            return uploaded_files
            
    def _get_content_type(self, filename: str) -> str:
        """根据文件扩展名获取MIME类型"""
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            '.md': 'text/markdown',
            '.txt': 'text/plain',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.json': 'application/json',
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.css': 'text/css',
            '.js': 'application/javascript',
        }
        return content_types.get(ext, 'application/octet-stream') 