"""
数据库架构更新脚本

此脚本用于：
- 更新现有数据库表结构
- 添加新的列
- 创建新的表
"""

from flask import Flask
from common.config import config
from common.db_setup import db
from sqlalchemy import inspect, text
import logging

# 创建临时Flask应用
app = Flask(__name__)
config.init_app(app)
db.init_app(app)

def update_user_table():
    """添加User表中缺失的列"""
    with app.app_context():
        engine = db.get_engine(bind='user_db')
        inspector = inspect(engine)
        
        # 获取现有列
        existing_columns = [col["name"] for col in inspector.get_columns("users")]
        
        # 需要添加的列及其定义
        columns_to_add = {
            "email": "VARCHAR(120)",
            "phone": "VARCHAR(20)",
            "real_name": "VARCHAR(50)",
            "bio": "TEXT",
            "location": "VARCHAR(100)",
            "website": "VARCHAR(200)",
            "last_login": "DATETIME"
        }
        
        # 添加缺失的列
        with engine.connect() as conn:
            for col_name, col_type in columns_to_add.items():
                if col_name not in existing_columns:
                    logging.info(f"添加列: {col_name}")
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
            
            conn.commit()
        logging.info("用户表更新完成")

def create_oauth_tables():
    """创建OAuth相关的表"""
    with app.app_context():
        try:
            # 导入OAuth模型以确保它们被注册
            from common.oauth_models import OAuthClient
            
            # 创建oauth_db绑定的所有表
            engine = db.engines.get('oauth_db')
            if engine:
                db.metadata.create_all(bind=engine, tables=[OAuthClient.__table__])
                logging.info("OAuth数据库表已创建")
            else:
                logging.error("无法获取oauth_db引擎")
                
        except Exception as e:
            logging.error(f"创建OAuth表时出错: {e}")
            raise

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logging.info("开始更新数据库结构...")
    try:
        update_user_table()
        create_oauth_tables()
        logging.info("数据库结构更新完成")
    except Exception as e:
        logging.error(f"更新数据库结构时出错: {e}")
        raise