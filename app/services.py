import os
import tempfile
import subprocess
import shutil
import time
import random
import string
import urllib.parse
import re
from typing import Optional, Tuple, Dict
import requests

from app.cos_service import COSService


class PDFConverterService:
    """PDF转Markdown服务"""

    def __init__(self):
        """初始化服务"""
        # 初始化腾讯云COS服务
        self.cos_service = COSService()
    
    def download_pdf(self, url: str) -> Optional[str]:
        """
        从URL下载PDF文件

        Args:
            url: PDF文件的URL

        Returns:
            临时文件路径，如果下载失败则返回None
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # 从URL获取原始文件名
            parsed_url = urllib.parse.urlparse(url)
            original_filename = os.path.basename(parsed_url.path)
            
            # 如果URL中没有文件名或不是PDF，使用默认名称
            if not original_filename or not original_filename.lower().endswith('.pdf'):
                original_filename = "document.pdf"
            
            # 生成8位随机字符串
            random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            
            # 分离文件名和扩展名
            base_name, extension = os.path.splitext(original_filename)
            
            # 创建临时文件夹
            temp_dir = tempfile.mkdtemp()
            
            # 构建新的文件名: 原始文件名_随机字符串.pdf
            new_filename = f"{base_name}_{random_suffix}{extension}"
            temp_file_path = os.path.join(temp_dir, new_filename)
            
            # 写入文件内容
            with open(temp_file_path, 'wb') as temp_file:
                temp_file.write(response.content)
            
            print(f"已下载PDF文件: {temp_file_path}")
            return temp_file_path
        except Exception as e:
            print(f"下载PDF文件失败: {e}")
            return None
    
    def replace_image_urls(self, markdown_text: str, files_dict: Dict[str, str]) -> str:
        """
        替换Markdown文本中的图片URL为COS远程URL
        
        Args:
            markdown_text: 原始Markdown文本
            files_dict: 文件路径和COS URL的映射字典
            
        Returns:
            替换了图片URL的Markdown文本
        """
        if not files_dict:
            return markdown_text
            
        # 创建一个按路径长度降序排序的文件字典（先匹配长路径，避免子路径误匹配）
        sorted_files = sorted(files_dict.items(), key=lambda x: len(x[0]), reverse=True)
        
        # 图片URL替换计数
        replace_count = 0
        
        # 查找Markdown中的图片引用格式: ![alt](path/to/image.ext)
        # 正则表达式解释:
        # !\[ - 开始，必须以![ 开头
        # [^]]* - 捕获组1，图片alt文本，除了]以外的任何字符
        # \]\( - 中间的](分隔符
        # ([^)]+) - 捕获组2，图片URL，除了)以外的任何字符
        # \) - 结束，必须以)结尾
        pattern = r'!\[([^]]*)\]\(([^)]+)\)'
        
        def replace_url(match):
            nonlocal replace_count
            alt_text = match.group(1)
            image_path = match.group(2)
            
            # 去除可能的URL参数和锚点
            image_path = image_path.split('#')[0].split('?')[0]
            
            # 如果已经是完整的HTTP/HTTPS URL，不做替换
            if image_path.startswith(('http://', 'https://')):
                return match.group(0)
                
            # 尝试找到对应的远程URL
            replaced = False
            for local_path, remote_url in sorted_files:
                # 检查本地路径是否匹配
                # 1. 完全匹配
                if local_path == image_path:
                    replaced = True
                    replace_count += 1
                    return f'![{alt_text}]({remote_url})'
                
                # 2. 图片引用可能使用相对路径，尝试匹配文件名部分
                image_filename = os.path.basename(image_path)
                if os.path.basename(local_path) == image_filename:
                    # 确保这是图片文件
                    ext = os.path.splitext(image_filename)[1].lower()
                    if ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp']:
                        replaced = True
                        replace_count += 1
                        return f'![{alt_text}]({remote_url})'
            
            # 如果没有找到匹配项，返回原始引用
            return match.group(0)
        
        # 执行替换
        new_markdown = re.sub(pattern, replace_url, markdown_text)
        
        print(f"图片URL替换完成，共替换了{replace_count}个图片引用")
        return new_markdown

    def convert_using_command(self, pdf_url: str) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, str]], Optional[str]]:
        """
        使用marker_single命令行工具从URL获取PDF并转换为Markdown，并上传到COS

        Args:
            pdf_url: PDF文件的URL

        Returns:
            元组 (转换后的Markdown文本, 主文件URL, 所有文件URL字典, 错误信息)
            如果处理成功，错误信息为None；如果处理失败，Markdown文本为None
        """
        pdf_path = None
        output_dir = None
        markdown_text = None
        file_url = None
        files_dict = None
        error_message = None
        pdf_dir_name = None

        try:
            # 步骤1: 下载PDF文件
            pdf_path = self.download_pdf(pdf_url)
            if not pdf_path:
                return None, None, None, "无法下载PDF文件"

            # 获取pdf文件名,去除.pdf后缀
            pdf_basename = os.path.basename(pdf_path)
            pdf_name = os.path.splitext(pdf_basename)[0]

            # 步骤2: 创建临时输出目录
            output_dir = tempfile.mkdtemp()
            
            # marker生成的文件夹名称 (pdf文件名)
            pdf_dir_name = pdf_name
            output_pdf_dir = os.path.join(output_dir, pdf_dir_name)
            output_file_path = os.path.join(output_pdf_dir, f"{pdf_name}.md")
            # 获取当前文件执行的绝对路径
            current_dir = os.path.dirname(os.path.abspath(__file__))

            # 步骤3: 执行marker_single命令 - 使用阻塞方式等待完成
            activate_command = f"source {current_dir}/../.venv/bin/activate"
            program = f"marker_single {pdf_path} --output_dir {output_dir}"

            cmd = ["bash", "-c", f'{activate_command} && {program}']
            print(f"开始执行命令: {' '.join(cmd)}")
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )

            # 步骤4: 检查命令执行结果
            print(f"命令执行完成，返回码: {process.returncode}")
            if process.returncode != 0:
                error_message = f"命令执行失败: {process.stderr}"
                return None, None, None, error_message

            # 步骤5: 等待短暂时间确保文件写入完成
            time.sleep(1)

            # 步骤6: 检查输出目录是否存在
            if not os.path.exists(output_pdf_dir):
                # 尝试列出输出目录中的内容
                available_files = []
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        available_files.append(os.path.join(root, file))
                error_message = f"转换后的目录不存在: {output_pdf_dir}。可用文件: {available_files}"
                return None, None, None, error_message

            # 步骤7: 读取生成的Markdown文件
            if os.path.exists(output_file_path):
                with open(output_file_path, 'r', encoding='utf-8') as f:
                    markdown_text = f.read()
                print(f"成功读取Markdown文件，长度: {len(markdown_text)}")
                
                # 步骤8: 上传整个目录到COS (除了主Markdown文件)
                # 生成COS上的基础路径：pdf文件名_时间戳
                timestamp = int(time.time())
                # 如果pdf_name以document开头，说明这个文件没有文件名，需要使用markdown内容中去提取文件名
                if pdf_name.startswith("document"):
                    # 提取markdown内容中的标题，第一个以#开头的行
                    pdf_name = re.search(r'^# (.*)', markdown_text, re.MULTILINE).group(1)
                    # 特殊符号处理，空格等全部替换为-
                    pdf_name = re.sub(r'[^\w\-]', '-', pdf_name)
                cos_base_path = f"tmp/{pdf_name}_{timestamp}"
                
                # 上传资源文件（图片等）
                print(f"开始上传资源文件到COS: {output_pdf_dir} -> {cos_base_path}")
                # 先上传除主Markdown文件外的所有文件
                files_dict = {}
                for root, dirs, files in os.walk(output_pdf_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 跳过主Markdown文件，我们将在替换URL后再上传它
                        if file_path == output_file_path:
                            continue
                        
                        # 计算相对路径
                        rel_path = os.path.relpath(file_path, output_pdf_dir)
                        # 上传文件并获取URL
                        file_url = self.cos_service.upload_file(file_path, f"{cos_base_path}/{rel_path}")
                        if file_url:
                            files_dict[rel_path] = file_url
                            
                # 步骤9: 替换Markdown中的图片引用为COS URL
                if files_dict:
                    markdown_text = self.replace_image_urls(markdown_text, files_dict)
                    print("已完成Markdown中图片引用的替换")
                    
                    # 将替换后的内容写回原文件
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_text)
                    print("已将替换后的内容写入原Markdown文件")
                
                # 步骤10: 上传替换后的Markdown文件
                main_md_rel_path = f"{pdf_name}.md"
                file_url = self.cos_service.upload_file(output_file_path, f"{cos_base_path}/{main_md_rel_path}")
                if file_url:
                    print(f"已上传替换后的Markdown文件: {file_url}")
                    files_dict[main_md_rel_path] = file_url
                else:
                    print("警告: 上传替换后的Markdown文件失败")
            else:
                available_files = []
                # 列出输出目录下的所有文件
                for root, dirs, files in os.walk(output_pdf_dir):
                    for file in files:
                        available_files.append(os.path.join(root, file))

                error_message = f"命令执行成功但未找到Markdown文件: {output_file_path}。可用文件: {available_files}"

        except Exception as e:
            error_message = f"执行命令时发生错误: {str(e)}"
        finally:
            # 步骤11: 清理临时文件 - 确保串行处理完成后再清理
            try:
                if pdf_path and os.path.exists(pdf_path):
                    # 删除PDF文件
                    os.unlink(pdf_path)
                    # 删除包含PDF的临时目录
                    pdf_temp_dir = os.path.dirname(pdf_path)
                    if pdf_temp_dir and os.path.exists(pdf_temp_dir) and pdf_temp_dir != output_dir:
                        shutil.rmtree(pdf_temp_dir, ignore_errors=True)
                    print(f"已删除临时PDF文件和目录: {pdf_path}")

                if output_dir and os.path.exists(output_dir):
                    shutil.rmtree(output_dir, ignore_errors=True)
                    print(f"已删除临时输出目录: {output_dir}")
            except Exception as cleanup_error:
                print(f"清理临时文件时发生错误: {cleanup_error}")

        # 所有处理完成后再返回结果
        return markdown_text, file_url, files_dict, error_message