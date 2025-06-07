from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

# 创建SQLAlchemy实例，但不立即初始化
db = SQLAlchemy()

def init_db(app):
    """
    初始化数据库
    
    Args:
        app: Flask应用实例
    """
    # 初始化SQLAlchemy
    db.init_app(app)
    
    # 导入模型以确保SQLAlchemy知道它们
    from common.UserInformation import UserApply
    
    with app.app_context():
        try:
            # 创建所有数据库表
            db.create_all()
            
            # 确保用户申请表存在
            engine = db.get_engine(bind='apply_db')
            inspector = inspect(engine)
            
            if not inspector.has_table("user_apply"):
                print("Creating user_apply table...")
                db.create_all(bind='apply_db')
            
            # 确保用户申请表包含所有必要的列
            columns = [col["name"] for col in inspector.get_columns("user_apply")]
            
            # 添加缺失的列
            if "status" not in columns:
                with engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE user_apply ADD COLUMN status BOOLEAN DEFAULT NULL"
                    ))
                    conn.commit()
            
            if "time" not in columns:
                with engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE user_apply ADD COLUMN time DATETIME DEFAULT CURRENT_TIMESTAMP"
                    ))
                    conn.commit()
                    
        except Exception as e:
            print(f"Database initialization error: {e}")
            # 在开发环境中可以重新创建表
            if app.debug:
                db.drop_all(bind='apply_db')
                db.create_all(bind='apply_db')