import unittest
from app.services import PDFConverterService

class TestImageURLReplacement(unittest.TestCase):
    """测试Markdown中图片URL替换功能"""
    
    def setUp(self):
        self.service = PDFConverterService()
        self.files_dict = {
            "image1.jpg": "https://example-bucket.cos.ap-guangzhou.myqcloud.com/tmp/doc_12345/image1.jpg",
            "images/image2.png": "https://example-bucket.cos.ap-guangzhou.myqcloud.com/tmp/doc_12345/images/image2.png",
            "subfolder/image3.jpeg": "https://example-bucket.cos.ap-guangzhou.myqcloud.com/tmp/doc_12345/subfolder/image3.jpeg",
            "doc.md": "https://example-bucket.cos.ap-guangzhou.myqcloud.com/tmp/doc_12345/doc.md"
        }
    
    def test_basic_image_replacement(self):
        """测试基本的图片URL替换"""
        markdown = """# 测试文档
        
这是一个测试，包含一些图片引用：

![图片1](image1.jpg)
        
正文继续...

![第二张图片](images/image2.png)

结束
"""
        expected = """# 测试文档
        
这是一个测试，包含一些图片引用：

![图片1](https://example-bucket.cos.ap-guangzhou.myqcloud.com/tmp/doc_12345/image1.jpg)
        
正文继续...

![第二张图片](https://example-bucket.cos.ap-guangzhou.myqcloud.com/tmp/doc_12345/images/image2.png)

结束
"""
        result = self.service.replace_image_urls(markdown, self.files_dict)
        self.assertEqual(result, expected)
    
    def test_no_replacement_for_external_urls(self):
        """测试不替换已经是完整URL的图片引用"""
        markdown = """# 测试文档
        
这是一个外部URL，不应该被替换：

![外部图片](https://external-site.com/image.jpg)

这是一个应该被替换的本地图片：

![本地图片](image1.jpg)
"""
        expected = """# 测试文档
        
这是一个外部URL，不应该被替换：

![外部图片](https://external-site.com/image.jpg)

这是一个应该被替换的本地图片：

![本地图片](https://example-bucket.cos.ap-guangzhou.myqcloud.com/tmp/doc_12345/image1.jpg)
"""
        result = self.service.replace_image_urls(markdown, self.files_dict)
        self.assertEqual(result, expected)
    
    def test_filename_only_matching(self):
        """测试通过文件名匹配的情况"""
        markdown = """# 测试文档
        
这个引用只使用了文件名，没有完整路径，但应该能匹配：

![简单引用](image3.jpeg)

这个引用路径与上传路径不同，但文件名相同，应该能匹配：

![不同路径](different/path/image2.png)
"""
        expected = """# 测试文档
        
这个引用只使用了文件名，没有完整路径，但应该能匹配：

![简单引用](https://example-bucket.cos.ap-guangzhou.myqcloud.com/tmp/doc_12345/subfolder/image3.jpeg)

这个引用路径与上传路径不同，但文件名相同，应该能匹配：

![不同路径](https://example-bucket.cos.ap-guangzhou.myqcloud.com/tmp/doc_12345/images/image2.png)
"""
        result = self.service.replace_image_urls(markdown, self.files_dict)
        self.assertEqual(result, expected)

if __name__ == "__main__":
    unittest.main() 