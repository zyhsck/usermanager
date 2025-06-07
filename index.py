from flask import Flask, render_template, redirect, url_for, session, request, jsonify, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename
import logging
import os
from uuid import uuid4

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建Flask应用
app = Flask(__name__)

# 加载配置
from common.Config import init_app
init_app(app)

# 初始化数据库
from common.db_setup import db, init_db
init_db(app)

# 导入模型和功能模块
from common.UserInformation import UserInformation, UserApply
from common.token_manager import TokenManager

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
                    'expires_in': int(current_app.config['OAUTH_TOKEN_EXPIRES'].total_seconds()),
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

    return render_template("dashboard.html", username=username, vip=vip, admin=admin)

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
        # 这里需要根据实际情况实现配置更新逻辑
        # 例如：更新应用配置、数据库配置等
        
        # 更新SMTP设置
        if 'smtp_settings' in config:
            smtp = config['smtp_settings']
            app.config['MAIL_SERVER'] = smtp.get('server')
            app.config['MAIL_PORT'] = smtp.get('port')
            app.config['MAIL_USERNAME'] = smtp.get('username')
            if smtp.get('password') and smtp.get('password') != '********':
                app.config['MAIL_PASSWORD'] = smtp.get('password')
            app.config['MAIL_USE_TLS'] = smtp.get('use_tls', False)
            app.config['MAIL_DEFAULT_SENDER'] = smtp.get('from_email')
        
        # 保存配置到配置文件或数据库
        # 这里需要根据实际情况实现配置持久化
        
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
    app.run(debug=True)