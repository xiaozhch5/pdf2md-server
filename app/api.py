from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models import ConversionRequest, ConversionResponse
from app.services import PDFConverterService

router = APIRouter(prefix="/api/v1", tags=["conversion"])

# 创建一个全局的PDF转换服务实例
pdf_converter_service = PDFConverterService()


@router.post("/convert", response_model=ConversionResponse, summary="将PDF转换为Markdown")
async def convert_pdf_to_markdown(request: ConversionRequest):
    """
    将PDF文件转换为Markdown（使用marker_single命令行工具）
    
    - **pdf_url**: PDF文件的URL
    
    返回:
    - 转换后的Markdown文件URL (替换完图片引用后的文件)
    """
    try:
        # 调用同步方法，确保完全串行处理
        print(f"开始处理PDF URL: {request.pdf_url}")
        markdown_text, file_url, files_dict, error = pdf_converter_service.convert_using_command(str(request.pdf_url))
        
        # 检查处理结果
        if not markdown_text:
            error_message = error if error else "未知错误"
            print(f"转换失败: {error_message}")
            raise HTTPException(status_code=400, detail=error_message)
        
        if not file_url:
            print("警告: 未能获取到Markdown文件URL")
            raise HTTPException(status_code=500, detail="无法获取转换后的Markdown文件URL")
        
        print(f"成功转换PDF，Markdown URL: {file_url}")
            
        return ConversionResponse(file_url=file_url)
    except Exception as e:
        print(f"处理请求时发生异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"转换过程中发生错误: {str(e)}"
        )


@router.get("/health", summary="健康检查")
async def health_check():
    """服务健康检查接口"""
    return JSONResponse(content={"status": "healthy"}, status_code=200) 