from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import sqlite3
import os

def migrate():
    """创建 oauth_clients 表（如果不存在）并添加 is_active 列"""
    try:
        # 获取数据库文件路径
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'oauth.db')
        
        # 连接到数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute('''
        SELECT name FROM sqlite_master WHERE type='table' AND name='oauth_clients'
        ''')
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # 创建表
            cursor.execute('''
            CREATE TABLE oauth_clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id VARCHAR(100) NOT NULL UNIQUE,
                client_secret VARCHAR(200) NOT NULL,
                name VARCHAR(100) NOT NULL,
                redirect_uri VARCHAR(500) NOT NULL,
                created_by VARCHAR(150) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
            ''')
            print("成功创建 oauth_clients 表")
        else:
            # 检查列是否存在
            cursor.execute('''
            PRAGMA table_info(oauth_clients)
            ''')
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'is_active' not in columns:
                # 添加 is_active 列
                cursor.execute('''
                ALTER TABLE oauth_clients 
                ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1
                ''')
                print("成功添加 is_active 列到 oauth_clients 表")
            else:
                print("is_active 列已经存在")
        
        # 提交更改
        conn.commit()
        print("成功添加 is_active 列到 oauth_clients 表")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("is_active 列已经存在")
        else:
            raise e
    except Exception as e:
        print(f"迁移失败: {e}")
        raise e
    finally:
        # 关闭数据库连接
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    migrate()