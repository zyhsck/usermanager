from flask import Flask, request, jsonify, render_template, url_for, session, redirect,make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_babel import Babel, _
import os
import subprocess
import atexit
from uuid import uuid4
from flask_session import Session
from datetime import datetime
import logging
import json
import redis
from common.UserInformation import UserInformation, UserApply, initialize_system
from common.oauth_routes import oauth_bp
from common.token_manager import TokenManager
from common.oauth_config import OAuthConfig
from common.ServerConfig import ServerConfig

logging.basicConfig(filename="log.log",level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# 动态获取数据库绝对路径
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../instance/user.db'))

'''
# 启动 sqlite-web 子进程
sqlite_web_process = subprocess.Popen(['sqlite_web', db_path])

def cleanup():
    sqlite_web_process.terminate()
    sqlite_web_process.wait()
'''

base_dir = os.path.abspath(os.path.dirname(__file__))
template_path = os.path.join(base_dir, '..', 'templates')
static_path = os.path.join(base_dir, '..', 'static')

app = Flask(__name__, template_folder=template_path, static_folder=static_path)

# 配置 Redis 作为 Session 存储
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.Redis(host='192.168.101.10', port=26739,password='123456')
app.config['SECRET_KEY'] = 'zyh123456'
app.config['SESSION_PERMANENT'] = False

app.config['UPLOAD_FOLDER'] = '/path/to/the/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
SETTINGS_FILE = 'settings.json'

Session(app)

# 多语言配置
app.config['BABEL_DEFAULT_LOCALE'] = 'zh'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'zh']
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

# 初始化 Babel
def get_locale():
    lang = request.cookies.get('lang') or 'zh'
    logging.info(f"Current language: {lang}, cookie value: {request.cookies.get('lang')}")
    return lang

babel = Babel(app, locale_selector=get_locale)
if 'BABEL_SUPPORTED_LOCALES' in app.config:
    logging.info("Babel initialized with supported locales: %s", app.config['BABEL_SUPPORTED_LOCALES'])



# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/user.db'
app.config['SQLALCHEMY_BINDS'] = {
    'user_db': 'sqlite:///../instance/user.db',
    'apply_db': 'sqlite:///../instance/apply.db',
    'oauth_db': 'sqlite:///../instance/oauth.db'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def ensure_user_apply_columns():
    with app.app_context():  # 重要：进入 app 上下文
        engine = db.get_engine(bind='apply_db')
        inspector = inspect(engine)

        columns = [col["name"] for col in inspector.get_columns("user_apply")]

        if "time" not in columns:
            with engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE user_apply ADD COLUMN time DATETIME DEFAULT CURRENT_TIMESTAMP"
                ))

