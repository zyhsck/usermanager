from flask import Flask, render_template, redirect, url_for, session, request, jsonify, make_response
from flask_cors import CORS
from flask_babel import Babel, gettext as _, ngettext
from werkzeug.utils import secure_filename
import logging
import os
from uuid import uuid4
from functools import wraps
from common.config import load_server_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建Flask应用
app = Flask(__name__)

# 初始化Babel
babel = Babel(app)

# 配置支持的语言
app.config['BABEL_DEFAULT_LOCALE'] = 'zh'
app.config['BABEL_LANGUAGES'] = ['zh', 'en']
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

def get_locale():
    # 优先从cookie中获取语言设置
    if request.cookies.get('lang'):
        return request.cookies.get('lang')
    # 如果cookie中没有，则从请求头中获取
    return request.accept_languages.best_match(app.config['BABEL_LANGUAGES'])

babel.localeselector_func = get_locale

# 添加翻译函数到模板全局变量
app.jinja_env.add_extension('jinja2.ext.i18n')
app.jinja_env.install_gettext_callables(
    gettext=_,
    ngettext=ngettext,
    newstyle=True
)

# 加载配置
from common.config import init_app
init_app(app)

# 初始化数据库
from common.db_setup import db, init_db
init_db(app)

# 导入模型和功能模块
from common.UserInformation import UserInformation, UserApply
from common.token_manager import TokenManager
from models import User

# 确保上传目录存在
if not os.path.exists('static/uploads'):
    os.makedirs('static/uploads')

@app.route('/')
def index():
    return redirect(url_for("home"))  # 访问自动跳转到其他网页

@app.before_request
def sync_user_permission():
    if session.get("IsLogin") and session.get("username"):
        user_info = UserInformation.get_user_info(session["username"])
        if user_info:
            session["vip"] = user_info["vip"]
            session["admin"] = user_info["admin"]

@app.route('/set_language/<lang_code>')
def set_language(lang_code):
    if lang_code not in ['en', 'zh']:
        lang_code = 'zh'  # 默认中文
    resp = make_response(redirect(request.referrer or url_for('home')))
    resp.set_cookie('lang', lang_code, max_age=30*24*60*60)  # 保存30天
    return resp

@app.route('/home')
def home():
    if session.get("IsLogin"):
        return render_template('index.html')
    else:
        return redirect(url_for("login"))

@app.route('/login', methods=["GET", "POST"])
def login():
    # 检查是否是OAuth流程
    is_oauth = request.args.get('oauth') == '1'
    
    if request.method == "GET":
        return render_template('login.html', is_oauth=is_oauth)
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user_info = UserInformation.verify_user(username, password)
        if user_info:
            redis_store = app.config.get('SESSION_REDIS')

            session["IsLogin"] = True
            session["username"] = user_info["username"]
            session["vip"] = user_info["vip"]
            session["admin"] = user_info["admin"]

            session_id = request.cookies.get('session') or session.sid if hasattr(session, 'sid') else str(uuid4())
            redis_store.set(f'user_session:{username}', session_id)

            # 如果是OAuth流程，生成令牌并重定向
            if 'oauth_client_id' in session and 'oauth_redirect_uri' in session:
                client_id = session['oauth_client_id']
                redirect_uri = session['oauth_redirect_uri']
                state = session.get('oauth_state', '')
                
                # 清除会话中的OAuth数据
                session.pop('oauth_client_id', None)
                session.pop('oauth_redirect_uri', None)
                session.pop('oauth_state', None)
                
                # 生成令牌并重定向
                access_token, refresh_token = TokenManager.generate_token(
                    username, 
                    client_id,
                    include_refresh_token=True
                )
                
                # 构建重定向URL
                from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
                url_parts = list(urlparse(redirect_uri))
                query = dict(parse_qsl(url_parts[4]))
                query.update({
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'Bearer',
                    'expires_in': int(app.config['OAUTH_TOKEN_EXPIRES'].total_seconds()),
                    'state': state
                })
                url_parts[4] = urlencode(query)
                return redirect(urlunparse(url_parts))
            
            return redirect(url_for("home"))
        else:
            return render_template('login.html', error="用户名或密码错误", is_oauth=is_oauth)

@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template('sign.html')
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        response, back_text = UserInformation.store_user(username, password)
        if response:
            return redirect(url_for("login"))
        else:
            return render_template('sign.html', error=back_text)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route('/dashboard')
def dashboard():
    if not session.get("IsLogin"):
        return redirect(url_for("login"))

    username = session.get("username")
    vip = session.get("vip")
    admin = session.get("admin")
    userdata = UserInformation.get_user_info(username)
    return render_template("dashboard.html", username=username, vip=vip, admin=admin, userdata=userdata)

@app.route('/apply', methods=["GET", "POST"])
def apply():
    if not session.get("IsLogin"):
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template('apply.html')
    elif request.method == "POST":
        username = session.get("username")
        permission = request.form.get("permission")
        reason = request.form.get("reason")
        response, back_text = UserApply.push_apply(username, permission, reason)
        if response:
            return render_template('apply.html', success=back_text)
        else:
            return render_template('apply.html', error=back_text)

@app.route('/apply_change', methods=["GET", "POST"])
def apply_change():
    if not session.get("IsLogin"):
        return redirect(url_for("login"))
    if not session.get("admin"):
        return redirect(url_for("home"))

    apply_list = UserApply.query.all()
    if request.method == "GET":
        return render_template('apply_change.html', apply_list=list(reversed(apply_list)))
    elif request.method == "POST":
        username = request.form.get("username")
        permission = request.form.get("permission")
        status = request.form.get("status")

        print(f"用户{username}的{permission}权限被设为{status}")

        try:
            result = UserApply.change_apply(username, permission, status)
            response, back_text = result
            if len(result) > 2:
                status = result[2]
                back_text += f", 用户{username}的{permission}权限被设为{status}"
        except Exception as e:
            logging.error(f"修改权限申请时出错: {e}")
            return render_template('apply_change.html', apply_list=apply_list, error=f"操作失败: {e}")

        if response:
            return render_template('apply_change.html', apply_list=apply_list, success=back_text)
        else:
            return render_template('apply_change.html', apply_list=apply_list, error=back_text)

@app.route('/user_manage', methods=["GET", "POST"])
def user_manage():
    if not session.get("IsLogin"):
        return redirect(url_for("login"))
    if not session.get("admin"):
        return redirect(url_for("home"))

    try:
        user_list = UserInformation.get_users_info_list()
        formatted_users = [
            {
                "id": idx,
                "time": user.get("register_time", ""),
                "username": user.get("username", ""),
                "permission": "管理员" if user.get("admin") else "普通用户",
                "vip": "拥有" if user.get("vip") else "无"
            }
            for idx, user in enumerate(user_list, start=1)
        ]
    except Exception as e:
        logging.error(f"获取用户信息时出错: {e}")
        return render_template('user_manage.html', user_list=[], error=f"加载用户信息失败: {e}")

    success = None
    error = None

    if request.method == "POST":
        delete_user = request.form.get("delete")
        username = request.form.get("username")
        
        # 处理添加用户请求
        add_username = request.form.get("add-username")
        add_password = request.form.get("add-password")
        add_vip = request.form.get("add-vip") == "1"
        add_admin = request.form.get("add-admin") == "1"
        
        if add_username and add_password:
            try:
                response, back_text = UserInformation.store_user(add_username, add_password, add_vip, add_admin)
                if response:
                    success = f"用户 {add_username} 已成功添加"
                    user_list = UserInformation.get_users_info_list()
                    formatted_users = [
                        {
                            "id": idx,
                            "time": user.get("register_time", ""),
                            "username": user.get("username", ""),
                            "permission": "管理员" if user.get("admin") else "普通用户",
                            "vip": "拥有" if user.get("vip") else "无"
                        }
                        for idx, user in enumerate(user_list, start=1)
                    ]
                    print(f"用户 {add_username} 已成功添加")

                else:
                    error = back_text
            except Exception as e:
                logging.error(f"添加用户时出错: {e}")
                error = f"添加用户失败: {e}"
        
        # 处理删除用户请求
        elif delete_user == "delete" and username:
            try:
                response, back_text = UserInformation.delete_user(username)
                if response:
                    success = f"用户 {username} 已成功删除"
                    user_list = UserInformation.get_users_info_list()
                    formatted_users = [
                        {
                            "id": idx,
                            "time": user.get("register_time", ""),
                            "username": user.get("username", ""),
                            "permission": "管理员" if user.get("admin") else "普通用户",
                            "vip": "拥有" if user.get("vip") else "无"
                        }
                        for idx, user in enumerate(user_list, start=1)
                    ]
                    print(f"用户 {username} 已成功删除")
                else:
                    error = back_text
            except Exception as e:
                logging.error(f"删除用户时出错: {e}")
                error = f"删除用户失败: {e}"

        # 处理权限修改请求
        elif request.form.get("username"):
            username = request.form.get("username")
            vip_status = request.form.get("vip") == "1"
            admin_status = request.form.get("admin") == "1"
            try:
                response, back_text, _ = UserApply.change_apply(username, "vip", "True" if vip_status else "False", need_entry=False)
                if response:
                    response, back_text, _ = UserApply.change_apply(username, "admin", "True" if admin_status else "False", need_entry=False)
                    if response:
                        success = f"用户 {username} 的权限已成功更新"
                        user_list = UserInformation.get_users_info_list()
                        formatted_users = [
                            {
                                "id": idx,
                                "time": user.get("register_time", ""),
                                "username": user.get("username", ""),
                                "permission": "管理员" if user.get("admin") else "普通用户",
                                "vip": "拥有" if user.get("vip") else "无"
                            }
                            for idx, user in enumerate(user_list, start=1)
                        ]
                    else:
                        error = back_text
                else:
                    error = back_text
            except Exception as e:
                logging.error(f"更新用户权限时出错: {e}")
                error = f"更新用户权限失败: {e}"

    return render_template(
        "user_manage.html",
        user_list=formatted_users,
        success=success,
        error=error
    )

@app.route('/setting')
def setting():
    if not session.get("IsLogin"):
        return redirect(url_for("login"))
    
    username = session.get("username")
    user_info = UserInformation.get_user_info(username)
    
    # 获取用户的OAuth客户端列表
    oauth_clients = []
    try:
        _, _, clients = UserInformation.manage_oauth_client('list', created_by=username)
        if clients:
            oauth_clients = clients
    except Exception as e:
        logging.error(f"获取OAuth客户端列表失败: {e}")
    
    # 如果是管理员，获取服务器配置
    server_config = None
    if session.get("admin"):
        try:
            server_config = UserInformation.get_server_info()
        except Exception as e:
            logging.error(f"获取服务器配置失败: {e}")
    
    return render_template('setting.html',
                         user_info=user_info,
                         oauth_clients=oauth_clients,
                         server_config=server_config)

@app.route('/api/settings/profile', methods=['POST'])
def update_profile():
    if not session.get("IsLogin"):
        return jsonify({"error": "未登录"}), 401
    
    username = session.get("username")
    try:
        # 初始化 profile_data
        profile_data = {}
        
        # 处理头像上传和表单数据
        if request.files:
            if 'usericon' in request.files:
                file = request.files['usericon']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join('static/uploads', filename))
                    profile_data['usericon_url'] = f'/static/uploads/{filename}'
            # 获取其他表单数据
            profile_data.update(request.form.to_dict())
        # 处理 JSON 数据
        elif request.is_json:
            profile_data = request.json
        # 处理普通表单数据
        else:
            profile_data = request.form.to_dict()
        
        # 确保 profile_data 不为空
        if not profile_data:
            return jsonify({"error": "没有提供要更新的数据"}), 400
        
        success, message = UserInformation.update_user_profile(username, profile_data)
        if success:
            return jsonify({"message": message})
        return jsonify({"error": message}), 400
        
    except Exception as e:
        logging.error(f"更新个人信息失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/settings/server', methods=['POST'])
def update_server_config():
    if not session.get("IsLogin") or not session.get("admin"):
        return jsonify({"error": "未授权"}), 403
    
    try:
        config = request.json
        
        # 更新服务器配置
        from common.config import Config
        
        # 更新应用配置
        if 'app_settings' in config:
            app_settings = config['app_settings']
            Config.update_app_config(
                debug=app_settings.get('debug'),
                secret_key=app_settings.get('secret_key'),
                session_lifetime=app_settings.get('session_lifetime')
            )
        
        # 更新数据库配置
        if 'database_settings' in config:
            db_settings = config['database_settings']
            Config.update_db_config(
                db_url=db_settings.get('db_url'),
                db_pool_size=db_settings.get('pool_size')
            )
        
        # 更新SMTP设置
        if 'smtp_settings' in config:
            smtp = config['smtp_settings']
            Config.update_smtp_config(
                server=smtp.get('server'),
                port=smtp.get('port'),
                username=smtp.get('username'),
                password=smtp.get('password') if smtp.get('password') != '********' else None,
                use_tls=smtp.get('use_tls', False),
                from_email=smtp.get('from_email')
            )
        
        # 更新Redis配置
        if 'redis_settings' in config:
            redis = config['redis_settings']
            Config.update_redis_config(
                url=redis.get('url'),
                password=redis.get('password') if redis.get('password') != '********' else None
            )
        
        return jsonify({"message": "服务器配置已更新"})
        
    except Exception as e:
        logging.error(f"更新服务器配置失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/oauth/clients', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_oauth_clients():
    if not session.get("IsLogin"):
        return jsonify({"error": "未登录"}), 401
    
    username = session.get("username")
    
    try:
        if request.method == 'GET':
            # 获取用户的OAuth客户端列表
            success, message, clients = UserInformation.manage_oauth_client('list', created_by=username)
            if success:
                client_list = []
                for client in clients:
                    client_list.append({
                        'client_id': client.client_id,
                        'name': client.name,
                        'redirect_uri': client.redirect_uri,
                        'created_at': client.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'is_active': client.is_active
                    })
                return jsonify(client_list)
            return jsonify({"error": message}), 400
            
        elif request.method == 'POST':
            # 创建新的OAuth客户端
            data = request.json
            success, message, client = UserInformation.manage_oauth_client(
                'create',
                name=data.get('name'),
                redirect_uri=data.get('redirect_uri'),
                created_by=username,
                is_active=data.get('is_active', True)
            )
            if success:
                return jsonify({
                    "message": message,
                    "client": {
                        "client_id": client.client_id,
                        "client_secret": client.client_secret,
                        "name": client.name,
                        "redirect_uri": client.redirect_uri,
                        "is_active": client.is_active
                    }
                })
            return jsonify({"error": message}), 400
            
        elif request.method == 'PUT':
            # 更新OAuth客户端
            data = request.json
            # 验证客户端所有权
            success, _, clients = UserInformation.manage_oauth_client('list', created_by=username)
            if not success or not any(c.client_id == data.get('client_id') for c in clients):
                return jsonify({"error": "无权修改此客户端"}), 403
                
            success, message, client = UserInformation.manage_oauth_client(
                'update',
                client_id=data.get('client_id'),
                name=data.get('name'),
                redirect_uri=data.get('redirect_uri'),
                is_active=data.get('is_active')
            )
            if success:
                return jsonify({"message": message})
            return jsonify({"error": message}), 400
            
        elif request.method == 'DELETE':
            # 删除OAuth客户端
            client_id = request.args.get('client_id')
            if not client_id:
                return jsonify({"error": "缺少client_id参数"}), 400
                
            # 验证客户端所有权
            success, _, clients = UserInformation.manage_oauth_client('list', created_by=username)
            if not success or not any(c.client_id == client_id for c in clients):
                return jsonify({"error": "无权删除此客户端"}), 403
                
            success, message, _ = UserInformation.manage_oauth_client('delete', client_id=client_id)
            if success:
                return jsonify({"message": message})
            return jsonify({"error": message}), 400
            
    except Exception as e:
        logging.error(f"管理OAuth客户端失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/user_data_manage')
def user_data_manage():
    """用户数据管理页面"""
    if not session.get("IsLogin"):
        return redirect(url_for("login"))
    if not session.get("admin"):
        return redirect(url_for("home"))
    
    from models import UserData
    all_data = UserData.query.all()
    
    # 将SQLAlchemy对象转换为字典列表
    formatted_data = [
        {
            'id': data.id,
            'user_id': data.user_id,
            'data_key': data.data_key,
            'data_value': data.data_value,
            'created_at': data.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': data.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        for data in all_data
    ]
    
    return render_template('user_data_manage.html', 
                         user_data=formatted_data,
                         username=session.get("username"))

@app.route('/api/user_data', methods=['GET', 'POST', 'DELETE'])
def handle_user_data():
    """
    用户数据API接口处理函数
    ---
    支持GET/POST/DELETE方法，用于操作用户数据
    GET:
      - 普通用户: 获取自己的数据(可指定key获取单个数据)
      - 管理员: 获取所有用户数据(需admin=true参数)
    POST:
      - 添加/更新用户数据(需提供key和value参数)
    DELETE:
      - 普通用户: 删除自己的数据(需key参数)
      - 管理员: 删除指定用户数据(需admin=true和username参数)
    权限控制:
      - 需登录(session中IsLogin为true)
      - 管理员操作需session中admin为true
    返回格式:
      - 成功: JSON格式数据
      - 失败: JSON格式错误信息及状态码
    错误码:
      - 400: 参数错误
      - 401: 未登录
      - 403: 权限不足
      - 404: 数据不存在
      - 500: 服务器错误
    """
    """
    用户数据API接口
    ---
    tags:
      - 用户数据
    parameters:
      - name: key
        in: query
        type: string
        required: false
        description: 数据键名
      - name: username
        in: query
        type: string
        required: false
        description: 目标用户名(仅管理员可用)
      - name: admin
        in: query
        type: boolean
        required: false
        description: 是否管理员操作

    
    if not session.get("IsLogin"):
        return jsonify({"error": "未登录"}), 401
    """
    from models import UserData, db
    username = session.get("username")
    is_admin = session.get("admin")
    server_info = load_server_config()
    # 检查server_token
    if request.is_json:
        data = request.json
        server_token = data.get('server_token')
        if server_token:
            try:
                
                if server_info and server_info.get('server_settings', {}).get('server_token') == server_token:
                    is_admin = True
                    username = data.get('username')  # 使用请求中的username
                    if not username:
                        return jsonify({"error": "使用server_token时必须提供username"}), 400
            except Exception as e:
                logging.error(f"验证server_token时出错: {e}")
                return jsonify({"error": f"验证server_token时出错: {str(e)}"}), 500
    
    if request.args.get('server_token'):
        if request.args.get('server_token') == server_info.get('server_settings', {}).get('server_token'):
            is_admin = True
            username = request.args.get('username')  # 使用URL参数中的username
            if not username:
                return jsonify({"error": "使用server_token时必须提供username"}), 400

    try:
        if request.method == 'GET':
            # 获取数据
            data_key = request.args.get('key')
            # 获取查询参数
            target_username = request.args.get('username')

            if is_admin:
                if target_username:
                    # 管理员查看指定用户的数据
                    user_exists = UserInformation.get_user_info(target_username)
                    if not user_exists:
                        return jsonify({"error": f"用户 {target_username} 不存在"}), 404
                    user_data = UserData.query.filter_by(user_id=target_username).all()
                else:
                    # 管理员查看所有数据
                    user_data = UserData.query.all()
                
                if user_data is None:
                    return jsonify({"error": "获取数据失败"}), 500
                
                # 尝试将JSON字符串转换回字典
                formatted_data = []
                for data in user_data:
                    try:
                        import json
                        data_value = data.data_value
                        if data_value and isinstance(data_value, str) and data_value.strip().startswith('{'):
                            data_value = json.loads(data_value)
                    except json.JSONDecodeError:
                        # 如果不是有效的JSON字符串，保持原样
                        data_value = data.data_value

                    formatted_data.append({
                        'id': data.id,
                        'user_id': data.user_id,
                        'data_key': data.data_key,
                        'data_value': data_value,
                        'created_at': data.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'updated_at': data.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                    })
                return jsonify(formatted_data)
            else:
                # 普通用户获取自己的数据
                if data_key:
                    user_data = UserData.query.filter_by(user_id=username, data_key=data_key).first()
                    api_token = request.args.get('api_token')
                    if api_token != UserInformation.get_user_info(username).get('api_token'):
                        return jsonify({"error": "API Token错误"}), 403
                    if user_data is None:
                        return jsonify({"error": "数据不存在"}), 404
                    # 尝试将JSON字符串转换回字典
                    try:
                        import json
                        data_value = user_data.data_value
                        if data_value and isinstance(data_value, str) and data_value.strip().startswith('{'):
                            data_value = json.loads(data_value)
                    except json.JSONDecodeError:
                        # 如果不是有效的JSON字符串，保持原样
                        data_value = user_data.data_value

                    return jsonify({
                        'id': user_data.id,
                        'user_id': user_data.user_id,
                        'data_key': user_data.data_key,
                        'data_value': data_value,
                        'created_at': user_data.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'updated_at': user_data.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                    })
                else:
                    user_data = UserData.query.filter_by(user_id=username).all()
                    return jsonify([{
                        'id': data.id,
                        'user_id': data.user_id,
                        'data_key': data.data_key,
                        'data_value': data.data_value,
                        'created_at': data.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'updated_at': data.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                    } for data in user_data])
                
        elif request.method == 'POST':
            # 添加/更新数据
            data = request.json
            if not data or 'key' not in data or 'value' not in data:
                return jsonify({"error": "缺少必要参数"}), 400
            
            # 确保用户已登录且username不为空
            if not username and not is_admin:
                return jsonify({"error": "用户未正确登录"}), 401
           
            # 数据验证
            if len(data['key']) > 50:
                return jsonify({"error": "键名过长(最大50字符)"}), 400
            if len(data['value']) > 1000:
                return jsonify({"error": "数据值过长(最大1000字符)"}), 400
                
            try:
                # 确定操作的用户
                target_username = data.get('username') if is_admin else username
                if not target_username:
                    target_username = username
                
                # 确保target_username不为None
                if target_username is None:
                    return jsonify({"error": "用户名不能为空"}), 400

                # 如果使用server_token，直接使用提供的username
                if server_token and server_token == server_info.get('server_settings', {}).get('server_token'):
                    target_username = data.get('username')
                    if not target_username:
                        return jsonify({"error": "使用server_token时必须提供username"}), 400
                
                # 检查用户是否存在
                user_exists = UserInformation.get_user_info(target_username)
                if not user_exists:
                    return jsonify({"error": f"用户 {target_username} 不存在"}), 404
                if is_admin:
                    api_token = request.args.get('api_token')
                    if api_token != UserInformation.get_user_info(username).get('api_token'):
                        return jsonify({"error": "API Token错误"}), 403
                # 使用用户名作为用户ID
                target_user_id = target_username

                import json  # 将json导入移到这里
                
                # 处理特殊键
                if data['key'] == 'profile':
                    # 确保value是字典类型
                    if not isinstance(data['value'], dict):
                        return jsonify({"error": "profile值必须是字典类型"}), 400
                    
                    # 获取现有用户数据
                    user_data = UserData.query.filter_by(user_id=target_username, data_key='profile').first()
                    if user_data:
                        try:
                            current_profile = json.loads(user_data.data_value) if user_data.data_value else {}
                        except json.JSONDecodeError:
                            current_profile = {}
                    else:
                        current_profile = {}
                    
                    # 更新profile
                    current_profile.update(data['value'])
                    data_value = json.dumps(current_profile)
                
                    # 更新或创建用户数据记录
                    if user_data:
                        user_data.data_value = data_value
                    else:
                        user_data = UserData(
                            user_id=target_username,
                            data_key='profile',
                            data_value=data_value
                        )
                        db.session.add(user_data)
                
                    try:
                        db.session.commit()
                        return jsonify({
                            "success": True,
                            "message": "数据保存成功",
                            "data": {
                                "username": target_username,
                                "key": data['key'],
                                "profile": current_profile
                            }
                        }), 200
                    except Exception as e:
                        db.session.rollback()
                        return jsonify({"error": f"保存数据失败: {str(e)}"}), 500
                else:
                    # 将字典类型的value转换为JSON字符串
                    data_value = data['value']
                    if isinstance(data_value, (dict, list)):
                        data_value = json.dumps(data_value)
                    elif not isinstance(data_value, str):
                        data_value = str(data_value)
                    
                    # 更新或创建普通用户数据记录
                    user_data = UserData.query.filter_by(
                        user_id=target_username,
                        data_key=data['key']
                    ).first()
                    
                    if user_data:
                        user_data.data_value = data_value
                    else:
                        user_data = UserData(
                            user_id=target_username,
                            data_key=data['key'],
                            data_value=data_value
                        )
                        db.session.add(user_data)
                    
                    try:
                        db.session.commit()
                        return jsonify({
                            "success": True,
                            "message": "数据保存成功",
                            "data": {
                                "username": target_username,
                                "key": data['key'],
                                "value": data['value']
                            }
                        }), 200
                    except Exception as e:
                        db.session.rollback()
                        return jsonify({"error": f"保存数据失败: {str(e)}"}), 500

                # 尝试更新现有数据
                user_data = UserData.query.filter_by(user_id=target_username, data_key=data['key']).first()
                if user_data:
                    user_data.data_value = data_value
                else:
                    # 使用UserData的add_data方法添加数据
                    result = UserData.add_data(
                        user_id=target_user_id,
                        data_key=data['key'],
                        data_value=data_value
                    )
                    
                    if isinstance(result, dict) and 'error' in result:
                        return jsonify(result), 400
                
                db.session.commit()
                return jsonify({
                    "message": "数据操作成功",
                    "data": {
                        "id": user_data.id,
                        "user_id": user_data.user_id,
                        "data_key": user_data.data_key,
                        "data_value": user_data.data_value,
                        "created_at": user_data.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        "updated_at": user_data.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                    }
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({"error": f"数据操作失败: {str(e)}"}), 400
            
        elif request.method == 'DELETE':
            # 删除数据
            data_key = request.args.get('key')
            if not data_key:
                return jsonify({"error": "缺少key参数"}), 400
            api_token = request.args.get('api_token')
            if api_token != UserInformation.get_user_info(username).get('api_token'):
                return jsonify({"error": "API Token错误"}), 403
            try:
                # 确定操作的用户
                target_username = request.args.get('username') if is_admin else username
                if not target_username:
                    target_username = username

                # 如果是管理员操作其他用户的数据，确保用户存在
                if is_admin and target_username != username:
                    user_exists = UserInformation.get_user_info(target_username)
                    if not user_exists:
                        return jsonify({"error": f"用户 {target_username} 不存在"}), 404

                # 查找要删除的数据
                user_data = UserData.query.filter_by(user_id=target_username, data_key=data_key).first()
                
                if user_data:
                    db.session.delete(user_data)
                    db.session.commit()
                    return jsonify({
                        "message": f"用户{target_username}数据{data_key}删除成功",
                        "data": None
                    })
                else:
                    return jsonify({
                        "error": f"用户{target_username}数据{data_key}不存在,注意需要server_token才能删除其他用户",
                        "data": None
                    }), 404
            except Exception as e:
                db.session.rollback()
                return jsonify({
                    "error": f"数据删除失败: {str(e)}",
                    "data": None
                }), 400
            
    except Exception as e:
        logging.error(f"用户数据操作失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/user_data/bulk', methods=['POST', 'DELETE'])
def handle_bulk_user_data():
    """
    批量操作用户数据API端点
    
    支持POST和DELETE方法，用于批量添加/更新/删除用户数据
    
    POST请求:
    - 参数: operations数组，包含多个操作对象
    - 每个操作对象必须包含:
      - key: 数据键名(最大50字符)
      - value: 数据值(最大1000字符)
      - action: 操作类型(add/update/delete/get)
    - 返回: 操作结果统计和失败详情
    
    DELETE请求:
    - 参数: operations数组或直接是键名列表
    - 每个操作对象必须包含:
      - key: 要删除的数据键名
      - action: 必须为'delete'
    - 返回: 删除结果统计和失败详情
    
    错误码:
    - 400: 参数错误
    - 401: 未登录
    - 403: 权限不足
    - 500: 服务器错误
    """
    """
    批量操作用户数据
    ---
    tags:
      - 用户数据
    parameters:
      - name: payload
        in: body
        required: true
        schema:
          type: object
          properties:
            operations:
              type: array
              items:
                type: object
                properties:
                  key:
                    type: string
                  value:
                    type: string
                  action:
                    type: string
                    enum: [add, update, delete]
    responses:
      200:
        description: 操作成功
      400:
        description: 参数错误
      401:
        description: 未登录
      403:
        description: 权限不足
      500:
        description: 服务器错误
    """
    if not session.get("IsLogin"):
        return jsonify({"error": "未登录"}), 401
    
    from models import UserData, db
    username = session.get("username")
    
    # 确保username不为空
    if username is None:
        return jsonify({"error": "用户未正确登录"}), 401
    
    try:
        if request.method == 'POST':
            # 批量添加数据
            data = request.json
            if not data or 'operations' not in data:
                return jsonify({"error": "缺少operations参数"}), 400
            
            data_list = data['operations']
            if not isinstance(data_list, list):
                return jsonify({"error": "operations必须是数组"}), 400
                
            # 数据验证
            for item in data_list:
                if not isinstance(item, dict) or 'key' not in item or 'value' not in item or 'action' not in item:
                    return jsonify({"error": "数据格式错误，每个操作必须包含key、value和action字段"}), 400
                if item['action'] not in ['add', 'update']:
                    continue
                if len(item['key']) > 50:
                    return jsonify({"error": f"键名过长(最大50字符): {item['key']}"}), 400
                if len(item['value']) > 1000:
                    return jsonify({"error": f"数据值过长(最大1000字符): {item['key']}"}), 400
            
            success_count = 0
            failed_operations = []
            try:
                for item in data_list:
                    try:
                        if item['action'] == 'get':
                            # 获取数据
                            user_data = UserData.query.filter_by(user_id=username, data_key=item['key']).first()
                            if user_data:
                                item['result'] = {
                                    'id': user_data.id,
                                    'user_id': user_data.user_id,
                                    'data_key': user_data.data_key,
                                    'data_value': user_data.data_value,
                                    'created_at': user_data.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                                    'updated_at': user_data.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                                }
                                success_count += 1
                            else:
                                failed_operations.append({
                                    'key': item['key'],
                                    'error': '数据不存在'
                                })
                        elif item['action'] in ['add', 'update']:
                            # 尝试更新现有数据
                            user_data = UserData.query.filter_by(user_id=username, data_key=item['key']).first()
                            if user_data and item['action'] == 'add':
                                # 如果是添加操作但数据已存在
                                failed_operations.append({
                                    'key': item['key'],
                                    'error': '数据已存在'
                                })
                                continue
                            elif not user_data and item['action'] == 'update':
                                # 如果是更新操作但数据不存在
                                failed_operations.append({
                                    'key': item['key'],
                                    'error': '数据不存在'
                                })
                                continue
                            
                            # 将字典类型的value转换为JSON字符串
                            data_value = item['value']
                            if isinstance(data_value, (dict, list)):
                                import json
                                data_value = json.dumps(data_value)
                            elif not isinstance(data_value, str):
                                data_value = str(data_value)

                            if user_data:
                                user_data.data_value = data_value
                            else:
                                # 检查用户是否存在
                                user_exists = UserInformation.get_user_info(username)
                                if not user_exists:
                                    failed_operations.append({
                                        'key': item['key'],
                                        'error': f"用户 {username} 不存在"
                                    })
                                    continue

                                # 使用UserData的add_data方法添加数据
                                result = UserData.add_data(
                                    user_id=username,
                                    data_key=item['key'],
                                    data_value=data_value
                                )
                            
                                if isinstance(result, dict) and 'error' in result:
                                    failed_operations.append({
                                        'key': item['key'],
                                        'error': result['error']
                                    })
                                    continue
                            success_count += 1
                            
                            # 返回操作结果
                            item['result'] = {
                                'id': user_data.id,
                                'user_id': user_data.user_id,
                                'data_key': user_data.data_key,
                                'data_value': user_data.data_value,
                                'created_at': user_data.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                                'updated_at': user_data.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                            }
                    except Exception as op_error:
                        failed_operations.append({
                            'key': item['key'],
                            'error': str(op_error)
                        })
                
                db.session.commit()
                return jsonify({
                    "message": f"批量操作完成，成功 {success_count} 条，失败 {len(failed_operations)} 条",
                    "success_count": success_count,
                    "total_count": len(data_list),
                    "failed_operations": failed_operations
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({
                    "error": f"批量操作失败: {str(e)}",
                    "success_count": success_count,
                    "total_count": len(data_list),
                    "failed_operations": failed_operations
                }), 400
            
        elif request.method == 'DELETE':
            # 批量删除数据
            data = request.json
            if not data or 'operations' not in data:
                # 兼容旧格式，直接是键名列表的情况
                keys = request.json
                if not isinstance(keys, list):
                    return jsonify({"error": "请求体必须是数组或包含operations数组的对象"}), 400
                
                success_count = 0
                failed_operations = []
                try:
                    for key in keys:
                        try:
                            user_data = UserData.query.filter_by(user_id=username, data_key=key).first()
                            if user_data:
                                db.session.delete(user_data)
                                success_count += 1
                            else:
                                failed_operations.append({
                                    'key': key,
                                    'error': '数据不存在'
                                })
                        except Exception as op_error:
                            failed_operations.append({
                                'key': key,
                                'error': str(op_error)
                            })
                    
                    db.session.commit()
                    return jsonify({
                        "message": f"批量删除完成，成功 {success_count} 条，失败 {len(failed_operations)} 条",
                        "success_count": success_count,
                        "total_count": len(keys),
                        "failed_operations": failed_operations
                    })
                except Exception as e:
                    db.session.rollback()
                    return jsonify({
                        "error": f"批量删除失败: {str(e)}",
                        "success_count": success_count,
                        "total_count": len(keys),
                        "failed_operations": failed_operations
                    }), 400
            else:
                # 新格式，使用operations数组
                data_list = data['operations']
                if not isinstance(data_list, list):
                    return jsonify({"error": "operations必须是数组"}), 400
                
                success_count = 0
                failed_operations = []
                try:
                    for item in data_list:
                        if not isinstance(item, dict) or 'key' not in item or 'action' not in item:
                            failed_operations.append({
                                'error': '数据格式错误，每个操作必须包含key和action字段'
                            })
                            continue
                        
                        if item['action'] != 'delete':
                            continue
                        
                        try:
                            user_data = UserData.query.filter_by(user_id=username, data_key=item['key']).first()
                            if user_data:
                                db.session.delete(user_data)
                                success_count += 1
                            else:
                                failed_operations.append({
                                    'key': item['key'],
                                    'error': '数据不存在'
                                })
                        except Exception as op_error:
                            failed_operations.append({
                                'key': item['key'],
                                'error': str(op_error)
                            })
                    
                    db.session.commit()
                    return jsonify({
                        "message": f"批量删除完成，成功 {success_count} 条，失败 {len(failed_operations)} 条",
                        "success_count": success_count,
                        "total_count": len(data_list),
                        "failed_operations": failed_operations
                    })
                except Exception as e:
                    db.session.rollback()
                    return jsonify({
                        "error": f"批量删除失败: {str(e)}",
                        "success_count": success_count,
                        "total_count": len(data_list),
                        "failed_operations": failed_operations
                    }), 400
            
    except Exception as e:
        logging.error(f"批量操作用户数据失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/<string:api_post>', methods=["POST"])
def api(api_post):
    username = request.json.get('username')
    api_token = request.json.get('api_token')
    if api_token is None:
        return jsonify({"error": "API token is required"}), 400

    if not UserInformation.verify_api_token(username, api_token):
        return jsonify({"error": "Invalid API token"}), 403

    api_posts = ["get_user_info", "get_server_info", "get_user_list", "delete_user"]

    if api_post not in api_posts:
        return jsonify({"error": "Invalid API request"}), 400

    try:
        match api_post:
            case "get_user_info":
                user_info = UserInformation.get_user_info(username)
                logging.info(f"用户 {username} 进行了获取用户信息的操作")
                return jsonify(user_info)
            case "get_server_info":
                server_info = UserInformation.get_server_info()
                logging.info(f"用户 {username} 进行了获取服务器信息的操作")
                return jsonify(server_info)
            case "get_user_list":
                user_list = UserInformation.get_users_name_list()
                logging.info(f"用户 {username} 进行了获取用户列表的操作")
                return jsonify(user_list)
            case "delete_user":
                witch_user = request.json.get('witch_user')
                if witch_user is None:
                    return jsonify({"error": "witch_user is required"}), 400
                response, back_text = UserInformation.delete_user(witch_user)
                if response:
                    logging.info(f"用户 {username} 进行了删除用户 {witch_user} 的操作")
                    return jsonify({"message": back_text})
                else:
                    return jsonify({"error": back_text}), 400
    except Exception as e:
        logging.error(f"API 请求处理时出错: {e}")
        return jsonify({"error": "API request failed"}), 500

# 注册OAuth蓝图
from common.oauth_routes import oauth_bp
app.register_blueprint(oauth_bp)

# 配置CORS
CORS(app, resources={
    r"/oauth/*": {"origins": "*"},  # 在生产环境中应该限制origins
    r"/api/*": {"origins": "*"}
})

if __name__ == '__main__':
    app.run(port=5004, debug=True)