from typing import Dict, Optional
from pydantic import BaseModel, HttpUrl


class ConversionRequest(BaseModel):
    """
    PDF转Markdown的请求模型
    """
    pdf_url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "pdf_url": "https://example.com/sample.pdf"
            }
        }


class ConversionResponse(BaseModel):
    """
    PDF转Markdown的响应模型
    """
    file_url: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_url": "https://example-bucket-1250000000.cos.ap-guangzhou.myqcloud.com/tmp/example_12345678/example.md"
            }
        } 