"""
app.py
溪山农服平台 — 后端 API 服务（Phase 1: Mock 数据版）

技术栈: Python + FastAPI + Uvicorn
数据源: data.py（对应前端 mock/test_data.js）
数据库: 暂不使用，后续接入 PostgreSQL

启动: python app.py  或  uvicorn app:app --host 0.0.0.0 --port 8000
"""

import time
import uuid
import os
import re
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from data import (
    USER_INFO, HOME_ALERT, HOME_REPORT,
    DISEASE_HISTORY, DETECTION_RESULT,
    ALERT_LIST, MY_PLOTS, PLOT_DETAIL,
    PEST_LIBRARY, PEST_DETAILS, SERVICE_RECORDS,
)
from llm_service import call_vision_llm, get_mode_info
from logger import get_logger, new_trace_id, set_trace_id, reset_trace_id, log_request
from database import init_database, get_db, User, Plot, DiseaseDetection
from auth_service import (
    register_user, login_user, get_current_user, get_current_user_optional,
    verify_token, create_access_token, create_refresh_token,
)

# ============================================================
# FastAPI 应用初始化
# ============================================================
app = FastAPI(
    title="溪山农服平台 API",
    description="Phase 1 — Mock 数据版，数据库就绪后替换为真实查询",
    version="1.0.0",
)

logger = get_logger(__name__)

# CORS 配置 — 允许小程序开发者工具和本地调试访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 开发环境: 允许所有来源; 生产环境需改为白名单
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/miniapp/v1"

# 启动时初始化数据库
init_database()

# 静态文件服务 — 上传的图像
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# ============================================================
# Trace ID 中间件 — 每个请求自动生成唯一追踪 ID
# ============================================================
@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """为每个 HTTP 请求注入 trace_id，贯穿整条调用链"""
    # 从请求头获取或生成新的 trace_id
    trace_id = request.headers.get("X-Trace-Id") or new_trace_id()
    token = set_trace_id(trace_id)

    start_time = time.time()

    # 记录请求开始
    logger.debug(
        f"→ {request.method} {request.url.path} "
        f"client={request.client.host if request.client else 'unknown'}"
    )

    try:
        response = await call_next(request)
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"✗ {request.method} {request.url.path} → 500 ({duration_ms:.0f}ms) "
            f"error={type(e).__name__}: {str(e)[:200]}"
        )
        reset_trace_id(token)
        raise

    # 计算耗时
    duration_ms = (time.time() - start_time) * 1000

    # 记录请求完成
    log_request(request.method, request.url.path, response.status_code, duration_ms)

    # 将 trace_id 写入响应头
    response.headers["X-Trace-Id"] = trace_id

    reset_trace_id(token)
    return response


# ============================================================
# 统一响应工具函数
# ============================================================
def success_response(data, message: str = "success"):
    """统一成功响应格式"""
    from logger import get_trace_id
    return {
        "code": 0,
        "message": message,
        "data": data,
        "request_id": get_trace_id(),
        "timestamp": int(time.time()),
    }


def error_response(code: int, message: str):
    """统一错误响应格式"""
    from logger import get_trace_id
    return {
        "code": code,
        "message": message,
        "data": None,
        "request_id": get_trace_id(),
        "timestamp": int(time.time()),
    }


# ============================================================
# 健康检查
# ============================================================
@app.get("/health")
async def health():
    """存活探针"""
    return {"status": "ok", "service": "xishan-agri-backend", "version": "1.0.0"}


@app.get("/ready")
async def ready():
    """就绪探针"""
    return {
        "status": "ok",
        "checks": {
            "data_module": "ok",
        },
        "time": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================
# 认证接口 — 注册 / 登录 / 刷新令牌
# ============================================================
class RegisterRequest(BaseModel):
    phone: str
    password: str
    name: str
    village: str = ""


class LoginRequest(BaseModel):
    phone: str
    password: str


class WechatLoginRequest(BaseModel):
    code: str


@app.post(f"{API_PREFIX}/auth/register")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册 — 手机号 + 密码 + 姓名"""
    try:
        result = register_user(db, req.phone, req.password, req.name, req.village)
        logger.info(f"注册成功: phone={req.phone}, name={req.name}")
        return success_response(result, "注册成功")
    except ValueError as e:
        logger.warning(f"注册失败: {e}")
        return JSONResponse(
            status_code=400,
            content=error_response(40001, str(e)),
        )


@app.post(f"{API_PREFIX}/auth/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录 — 手机号 + 密码 → JWT 令牌"""
    try:
        result = login_user(db, req.phone, req.password)
        logger.info(f"登录成功: phone={req.phone}")
        return success_response(result, "登录成功")
    except ValueError as e:
        logger.warning(f"登录失败: phone={req.phone}, reason={e}")
        return JSONResponse(
            status_code=401,
            content=error_response(40100, str(e)),
        )


@app.post(f"{API_PREFIX}/auth/wechat-login")
async def wechat_login(req: WechatLoginRequest, db: Session = Depends(get_db)):
    """
    微信小程序登录（保留兼容）
    前端 wx.login() 获取 code → 调用此接口
    Phase 1: 自动注册或登录（以 openid 为唯一标识）
    """
    # TODO: 对接微信 code2session API 获取 openid
    # Phase 1: 用 code 作为临时标识，自动创建/查找用户
    phone = f"wx_{req.code[:11]}"
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        # 自动注册
        result = register_user(db, phone, req.code, "微信用户")
    else:
        result = login_user(db, phone, req.code)
    return success_response(result)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@app.post(f"{API_PREFIX}/auth/refresh")
async def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    """刷新 access_token"""
    payload = verify_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        return JSONResponse(
            status_code=401,
            content=error_response(40101, "刷新令牌无效或已过期"),
        )
    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(
            status_code=401,
            content=error_response(40101, "用户不存在"),
        )
    return success_response({
        "access_token": create_access_token(user.id, user.phone),
        "refresh_token": create_refresh_token(user.id),
        "expires_in": 86400,
    })


# ============================================================
# 用户接口 — 需要认证
# ============================================================
@app.get(f"{API_PREFIX}/user/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return success_response({
        "name": current_user.name,
        "village": current_user.village or "",
        "avatar": current_user.avatar or "",
        "phone": current_user.phone,
        "stats": USER_INFO["stats"],  # TODO: 从数据库统计
    })


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    village: Optional[str] = None


@app.post(f"{API_PREFIX}/user/profile/update")
async def update_profile(req: UpdateProfileRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """更新用户信息"""
    if req.name is not None:
        current_user.name = req.name
    if req.avatar is not None:
        current_user.avatar = req.avatar
    if req.village is not None:
        current_user.village = req.village
    db.commit()
    logger.info(f"用户信息更新: user_id={current_user.id}")
    return success_response(None, "更新成功")


@app.get(f"{API_PREFIX}/user/stats")
async def get_user_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取用户统计（地块数/识别次数/巡田次数）"""
    plot_count = db.query(Plot).filter(Plot.user_id == current_user.id).count()
    detection_count = db.query(DiseaseDetection).filter(DiseaseDetection.user_id == current_user.id).count()
    total_area = sum(p.area for p in db.query(Plot).filter(Plot.user_id == current_user.id).all() if p.area)
    return success_response({
        "area": float(total_area or 0),
        "plots": plot_count,
        "patrols": detection_count,  # 暂用识别次数代替
    })


@app.get(f"{API_PREFIX}/user/service-records")
async def get_service_records(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取服务记录列表"""
    detection_count = db.query(DiseaseDetection).filter(DiseaseDetection.user_id == current_user.id).count()
    return success_response([
        {"name": "识病记录", "count": f"{detection_count}条", "icon": "🔬", "color": "#E8F0E4"},
        {"name": "巡田报告", "count": "0次", "icon": "📋", "color": "#FCF0D9"},
        {"name": "飞防订单", "count": "0单", "icon": "🛩️", "color": "#FBE8E5"},
    ])


# ============================================================
# 首页接口
# ============================================================
@app.get(f"{API_PREFIX}/home/alert")
async def get_home_alert():
    """首页最新预警卡片"""
    return success_response(HOME_ALERT)


@app.get(f"{API_PREFIX}/home/report")
async def get_home_report():
    """首页巡田报告卡片"""
    return success_response(HOME_REPORT)


# ============================================================
# 地块接口 — 需要认证，数据按用户隔离
# ============================================================
@app.get(f"{API_PREFIX}/plots/mine")
async def get_my_plots(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户的地块列表"""
    plots = db.query(Plot).filter(Plot.user_id == current_user.id).all()
    result = []
    for p in plots:
        result.append({
            "id": f"plot-{p.id}",
            "_db_id": p.id,
            "name": p.name,
            "crop": p.crop or "",
            "area": float(p.area) if p.area else 0,
            "healthScore": p.health_score or 80,
            "lastPatrol": p.last_patrol.strftime("%Y-%m-%d") if p.last_patrol else "",
        })
    return success_response(result)


@app.get(f"{API_PREFIX}/plots/{{plot_id}}")
async def get_plot_detail(plot_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取地块详情"""
    # 兼容 plot-xxx 格式
    db_id = int(plot_id.replace("plot-", "")) if plot_id.startswith("plot-") else None
    if not db_id:
        # 回退到 mock 数据
        if plot_id == PLOT_DETAIL["id"]:
            return success_response(PLOT_DETAIL)
        return JSONResponse(status_code=404, content=error_response(40400, f"地块不存在: {plot_id}"))

    plot = db.query(Plot).filter(Plot.id == db_id, Plot.user_id == current_user.id).first()
    if not plot:
        return JSONResponse(status_code=404, content=error_response(40400, f"地块不存在: {plot_id}"))

    # 获取该地块的识别记录
    detections = db.query(DiseaseDetection).filter(DiseaseDetection.plot_id == plot.id).all()
    findings = []
    for d in detections:
        findings.append({
            "pest": d.disease_name,
            "severity": d.severity,
            "advice": d.symptoms or "",
        })

    return success_response({
        "id": f"plot-{plot.id}",
        "name": plot.name,
        "healthScore": plot.health_score or 80,
        "healthLevel": "良好" if (plot.health_score or 80) >= 75 else "需关注",
        "crop": plot.crop or "",
        "area": float(plot.area) if plot.area else 0,
        "lastPatrol": plot.last_patrol.strftime("%Y-%m-%d") if plot.last_patrol else "",
        "findings": findings if findings else PLOT_DETAIL["findings"],
        "trend": PLOT_DETAIL["trend"],  # TODO: 从历史数据计算
    })


@app.get(f"{API_PREFIX}/plots/{{plot_id}}/health-trend")
async def get_health_trend(plot_id: str, current_user: User = Depends(get_current_user)):
    """获取地块健康度趋势"""
    return success_response(PLOT_DETAIL["trend"])  # TODO: 从历史数据计算


@app.get(f"{API_PREFIX}/plots/{{plot_id}}/reports")
async def get_patrol_reports(plot_id: str, current_user: User = Depends(get_current_user)):
    """获取地块巡田报告列表"""
    return success_response([])


# ============================================================
# 病虫害识别接口 — 需要认证，结果存入数据库
# ============================================================
@app.post(f"{API_PREFIX}/disease/identify")
async def identify_disease(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    拍照识病 — 上传图片，调用大模型识别，保存图片和结果到数据库
    """
    image_bytes = await file.read()
    image_type = file.content_type or "image/jpeg"
    image_size_kb = len(image_bytes) / 1024

    logger.info(
        f"拍照识病请求: user_id={current_user.id}, filename={file.filename}, "
        f"size={image_size_kb:.1f}KB"
    )

    try:
        result = await call_vision_llm(image_bytes, image_type)

        # 先保存识别记录以获取数据库 ID
        detection = DiseaseDetection(
            user_id=current_user.id,
            disease_name=result.get("diseaseName", "未知"),
            severity=result.get("severity", "low"),
            confidence=result.get("confidence", 0.5),
            image_path="",  # 先占位，下面填
            symptoms=result.get("symptoms", ""),
            treatments=result.get("treatments", []),
            crop_type=result.get("cropType", ""),
        )
        db.add(detection)
        db.commit()
        db.refresh(detection)

        # 保存上传的图片到磁盘
        ext = "jpg" if "jpeg" in image_type else image_type.split("/")[-1]
        image_filename = f"detection_{detection.id}.{ext}"
        image_filepath = os.path.join(UPLOAD_DIR, image_filename)
        with open(image_filepath, "wb") as f:
            f.write(image_bytes)

        # 更新数据库中的图片路径
        detection.image_path = image_filename
        db.commit()

        logger.info(
            f"识别完成并已保存: detection_id={detection.id}, "
            f"image={image_filename}, "
            f"disease={result.get('diseaseName')}, "
            f"severity={result.get('severity')}, "
            f"confidence={result.get('confidence', 0):.2f}"
        )

        # 返回时加上数据库 ID 和图片 URL
        result["detection_id"] = f"D{detection.id}"
        result["id"] = f"D{detection.id}"
        result["imageUrl"] = f"/uploads/{image_filename}"
        return success_response(result)

    except Exception as e:
        logger.error(f"AI 识别失败: {type(e).__name__}: {str(e)[:300]}")
        return JSONResponse(
            status_code=503,
            content=error_response(50300, f"AI 识别服务暂时不可用: {str(e)}"),
        )


@app.get(f"{API_PREFIX}/disease/history")
async def get_disease_history(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的识别历史记录（分页）"""
    query = db.query(DiseaseDetection).filter(DiseaseDetection.user_id == current_user.id)
    total = query.count()
    items_db = query.order_by(DiseaseDetection.detected_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = []
    for d in items_db:
        items.append({
            "id": f"D{d.id}",
            "name": d.disease_name,
            "severity": d.severity,
            "plotName": "",
            "date": d.detected_at.strftime("%Y-%m-%d") if d.detected_at else "",
            "thumbnail": f"/uploads/{d.image_path}" if d.image_path else "",
        })

    return success_response({
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        }
    })


@app.delete(f"{API_PREFIX}/disease/history/{{record_id}}")
async def delete_disease_history(
    record_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除识别历史记录（只能删除自己的）"""
    try:
        db_id = int(re.findall(r"\d+", record_id)[0])
    except (ValueError, IndexError):
        return error_response(400, "无效的记录 ID")

    record = db.query(DiseaseDetection).filter(
        DiseaseDetection.id == db_id,
        DiseaseDetection.user_id == current_user.id
    ).first()

    if not record:
        return error_response(404, "记录不存在或无权操作")

    # 删除关联的图片文件
    if record.image_path:
        img_path = os.path.join(UPLOAD_DIR, record.image_path)
        if os.path.exists(img_path):
            os.remove(img_path)

    db.delete(record)
    db.commit()

    return success_response(None, "删除成功")


@app.get(f"{API_PREFIX}/disease/result/{{detection_id}}")
async def get_detection_result(detection_id: str):
    """获取识别结果详情"""
    # 从历史记录中查找
    for record in DISEASE_HISTORY:
        if record["id"] == detection_id:
            return success_response({
                "detection_id": record["id"],
                "diseaseName": record["name"],
                "severity": record["severity"],
                "plotName": record["plotName"],
                "time": record["date"],
                "treatments": DETECTION_RESULT["treatments"],
            })
    return JSONResponse(
        status_code=404,
        content=error_response(40400, f"识别记录不存在: {detection_id}")
    )


@app.get(f"{API_PREFIX}/disease/pest-library")
async def get_pest_library():
    """获取病虫害知识库列表"""
    return success_response(PEST_LIBRARY)


@app.get(f"{API_PREFIX}/disease/pest-library/{{pest_id}}")
async def get_pest_detail(pest_id: str):
    """获取病虫害详情（症状/防治方案）"""
    detail = PEST_DETAILS.get(pest_id)
    if detail:
        return success_response(detail)
    return JSONResponse(
        status_code=404,
        content=error_response(40400, f"病虫害不存在: {pest_id}")
    )


# ============================================================
# 预警接口
# ============================================================
@app.get(f"{API_PREFIX}/alerts")
async def get_alerts(severity: Optional[str] = None, page: int = 1, page_size: int = 20):
    """获取预警列表（支持按严重度筛选 + 分页）"""
    filtered = ALERT_LIST
    if severity:
        filtered = [a for a in ALERT_LIST if a["severity"] == severity]

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]

    return success_response({
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        }
    })


@app.get(f"{API_PREFIX}/alerts/unread-count")
async def get_unread_count():
    """获取未处理预警数量"""
    return success_response({"count": len(ALERT_LIST)})


@app.get(f"{API_PREFIX}/alerts/{{alert_id}}")
async def get_alert_detail(alert_id: str):
    """获取预警详情"""
    for alert in ALERT_LIST:
        if alert["id"] == alert_id:
            return success_response(alert)
    return JSONResponse(
        status_code=404,
        content=error_response(40400, f"预警不存在: {alert_id}")
    )


# ============================================================
# 全局异常处理
# ============================================================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} path={request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.status_code * 100, exc.detail),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"未捕获异常: {type(exc).__name__}: {str(exc)[:300]} path={request.url.path}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content=error_response(50000, "服务器内部错误"),
    )


# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("溪山农服平台 — 后端 API 服务启动")
    logger.info("Phase 1: Mock 数据 + 硅基流动视觉大模型")
    logger.info(get_mode_info())
    logger.info("服务地址: http://localhost:8000")
    logger.info("API 文档: http://localhost:8000/docs")
    logger.info("日志目录: backend/logs/")
    logger.info("=" * 60)

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
    )
