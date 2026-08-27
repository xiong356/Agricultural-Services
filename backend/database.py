"""
database.py
溪山农服平台 — 数据库层（SQLAlchemy ORM）

支持 MySQL 和 SQLite 双模式:
  - MySQL (生产): DB_URL=mysql+pymysql://root:password@localhost:3306/xishan_agri
  - SQLite (开发): DB_URL=sqlite:///./xishan_agri.db (默认，零安装即可用)

切换方式: 在 backend/.env 中设置 DB_URL

MySQL 安装:
  1. 下载: https://dev.mysql.com/downloads/installer/
  2. 安装时设置 root 密码
  3. 创建数据库: CREATE DATABASE xishan_agri CHARACTER SET utf8mb4;
  4. 在 .env 中配置: DB_URL=mysql+pymysql://root:你的密码@localhost:3306/xishan_agri
"""

import os
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DECIMAL,
    DateTime, Date, ForeignKey, JSON, text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from sqlalchemy.pool import StaticPool

from logger import get_logger

logger = get_logger(__name__)

# ============================================================
# 配置 — 从 .env 读取数据库 URL，默认 SQLite
# ============================================================

def _load_env():
    config = {}
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip().strip('"').strip("'")
    return config

_env = _load_env()

DB_URL = os.getenv("DB_URL") or _env.get("DB_URL", "")

if not DB_URL:
    # 默认使用 SQLite（零安装即可运行）
    _db_path = os.path.join(os.path.dirname(__file__), "xishan_agri.db")
    DB_URL = f"sqlite:///{_db_path}"
    DB_TYPE = "sqlite"
else:
    DB_TYPE = "mysql" if "mysql" in DB_URL else "sqlite"

logger.info(f"数据库类型: {DB_TYPE}, URL: {DB_URL.replace('://', '://***') if 'password' in DB_URL else DB_URL}")

# ============================================================
# SQLAlchemy 引擎
# ============================================================

_engine_kwargs = {"echo": False}

if DB_TYPE == "sqlite":
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DB_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入: 获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# 数据模型
# ============================================================

class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100))
    village = Column(String(100))
    role = Column(String(20), default="farmer")
    avatar = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    plots = relationship("Plot", back_populates="user", cascade="all, delete-orphan")
    detections = relationship("DiseaseDetection", back_populates="user", cascade="all, delete-orphan")


class Plot(Base):
    """地块表（用户关联）"""
    __tablename__ = "plots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    crop = Column(String(50))
    area = Column(DECIMAL(10, 2))
    health_score = Column(Integer, default=80)
    last_patrol = Column(Date)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="plots")
    detections = relationship("DiseaseDetection", back_populates="plot")


class DiseaseDetection(Base):
    """病虫害识别记录（用户关联）"""
    __tablename__ = "disease_detections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plot_id = Column(Integer, ForeignKey("plots.id", ondelete="SET NULL"), nullable=True)
    disease_name = Column(String(200))
    severity = Column(String(20))
    confidence = Column(DECIMAL(4, 3))
    image_path = Column(Text, default="")
    symptoms = Column(Text, default="")
    treatments = Column(JSON)  # JSON 格式存储防治方案
    crop_type = Column(String(50), default="")
    detected_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="detections")
    plot = relationship("Plot", back_populates="detections")


# ============================================================
# 数据库初始化
# ============================================================

def init_database():
    """创建所有表（如果不存在）"""
    logger.info("正在初始化数据库表...")
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")

    # 检查是否需要插入种子数据
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            _seed_data(db)
            logger.info("种子数据已插入（测试用户 + 示例地块）")
        else:
            logger.info(f"数据库已有 {user_count} 个用户，跳过种子数据")
    finally:
        db.close()


def _seed_data(db: Session):
    """插入测试数据"""
    import bcrypt

    # 测试用户
    test_password = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
    test_user = User(
        phone="13800138000",
        password_hash=test_password,
        name="张大哥",
        village="王家村",
        role="farmer",
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    # 示例地块
    plots_data = [
        {"name": "王家村 A-03", "crop": "水稻", "area": 4.2, "health_score": 78, "last_patrol": date(2026, 7, 14)},
        {"name": "李家村 B-01", "crop": "蔬菜", "area": 3.5, "health_score": 92, "last_patrol": date(2026, 7, 10)},
        {"name": "张家村 C-01", "crop": "水稻", "area": 2.5, "health_score": 85, "last_patrol": date(2026, 7, 8)},
    ]
    for p in plots_data:
        plot = Plot(user_id=test_user.id, **p)
        db.add(plot)
    db.commit()

    # 示例识别记录
    detections_data = [
        {"disease_name": "稻瘟病", "severity": "medium", "confidence": 0.93, "crop_type": "水稻",
         "symptoms": "叶片出现梭形病斑", "treatments": [
             {"label": "药剂推荐", "value": "三环唑 20g/亩"},
             {"label": "防治窗口", "value": "3-5天内喷施"},
             {"label": "飞防参数", "value": "航高2.5m · 喷幅4m"}]},
        {"disease_name": "稻飞虱", "severity": "medium", "confidence": 0.88, "crop_type": "水稻",
         "symptoms": "稻株基部吸食汁液", "treatments": [
             {"label": "药剂推荐", "value": "吡虫啉 10g/亩"},
             {"label": "防治窗口", "value": "3-5天内"},
             {"label": "飞防参数", "value": "航高2.5m · 喷幅5m"}]},
    ]
    for d in detections_data:
        detection = DiseaseDetection(user_id=test_user.id, **d)
        db.add(detection)
    db.commit()

    logger.info(f"种子数据: 1 个用户(手机 13800138000, 密码 123456), 3 个地块, 2 条识别记录")
