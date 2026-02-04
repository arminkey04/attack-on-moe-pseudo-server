"""
Parse Config API Router
提供服务器配置信息，用于版本检查等
"""
from fastapi import APIRouter, Request
from typing import Dict, Any

router = APIRouter(prefix="/parse", tags=["config"])

# 服务器配置参数
# 这些参数会被客户端用于版本检查等功能
CONFIG_PARAMS: Dict[str, Any] = {
    # 版本号 - 客户端会检查这个版本号来决定是否需要更新
    # 设置为与客户端相同的版本号，这样就不会强制更新
    "Version_Android": "2.5.2",
    "Version_iOS": "2.5.0",

    # 其他可选配置参数
    "maintenanceMode": False,
    "maintenanceMessage": "",
    "serverVersion": "1.0.0",
}


@router.get("/config")
async def get_config(request: Request):
    """
    获取服务器配置

    Parse SDK 会调用这个端点来获取服务器配置参数
    客户端使用 Version_Android/Version_iOS 来检查是否需要更新

    Returns:
        {"params": {...}} 格式的配置对象
    """
    return {"params": CONFIG_PARAMS}


@router.post("/config")
async def get_config_post(request: Request):
    """
    获取服务器配置 (POST 方法)

    某些版本的 Parse SDK 可能使用 POST 方法请求配置
    """
    return {"params": CONFIG_PARAMS}
