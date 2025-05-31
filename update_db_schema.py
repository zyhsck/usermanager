from common.Config import app, db
from sqlalchemy import inspect, text
import logging

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
                    print(f"添加列: {col_name}")
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
            
            conn.commit()

def create_oauth_tables():
    """创建OAuth相关的表"""
    with app.app_context():
        # 导入OAuth模型以确保它们被注册
        from common.oauth_models import OAuthClient
        
        # 创建oauth_db绑定的所有表
        engine = db.engines.get('oauth_db')
        if engine:
            db.metadata.create_all(bind=engine, tables=[OAuthClient.__table__])
            print("OAuth数据库表已创建")
        else:
            print("无法获取oauth_db引擎")

if __name__ == "__main__":
    print("开始更新数据库结构...")
    update_user_table()
    create_oauth_tables()
    print("数据库结构更新完成")