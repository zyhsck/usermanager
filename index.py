from common.Config import *
from flask_cors import CORS
import logging
from uuid import uuid4

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
            redis_store = app.config['SESSION_REDIS']
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
                token = TokenManager.generate_token(username, client_id)
                
                # 构建重定向URL
                from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
                url_parts = list(urlparse(redirect_uri))
                query = dict(parse_qsl(url_parts[4]))
                query.update({
                    'token': token,
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
    server_config = ServerConfig.load_config()
    
    # 获取用户的OAuth客户端列表
    oauth_clients = []
    try:
        _, _, clients = UserInformation.manage_oauth_client('list', created_by=username)
        if clients:
            oauth_clients = clients
    except Exception as e:
        logging.error(f"获取OAuth客户端列表失败: {e}")
    
    return render_template('setting.html',
                         user_info=user_info,
                         server_config=server_config,
                         oauth_clients=oauth_clients)

@app.route('/api/settings/profile', methods=['POST'])
def update_profile():
    if not session.get("IsLogin"):
        return jsonify({"error": "未登录"}), 401
    
    username = session.get("username")
    try:
        # 处理头像上传
        if 'usericon' in request.files:
            file = request.files['usericon']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join('static/uploads', filename))
                profile_data = request.form.to_dict()
                profile_data['usericon_url'] = f'/static/uploads/{filename}'
        else:
            profile_data = request.json or {}
        
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
        return jsonify({"error": "无权限"}), 403
    
    try:
        config_updates = request.json
        if ServerConfig.update_config(config_updates):
            return jsonify({"message": "服务器配置已更新"})
        return jsonify({"error": "更新服务器配置失败"}), 400
        
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
            success, message, clients = UserInformation.manage_oauth_client('list', created_by=username)
            if success:
                return jsonify({"clients": [
                    {
                        "client_id": c.client_id,
                        "name": c.name,
                        "redirect_uri": c.redirect_uri,
                        "created_at": c.created_at.isoformat()
                    } for c in clients
                ]})
        
        elif request.method == 'POST':
            data = request.json
            success, message, client = UserInformation.manage_oauth_client(
                'create',
                name=data['name'],
                redirect_uri=data['redirect_uri'],
                created_by=username
            )
            if success:
                return jsonify({
                    "message": message,
                    "client": {
                        "client_id": client.client_id,
                        "client_secret": client.client_secret,
                        "name": client.name,
                        "redirect_uri": client.redirect_uri
                    }
                })
        
        elif request.method == 'PUT':
            data = request.json
            success, message, client = UserInformation.manage_oauth_client(
                'update',
                client_id=data['client_id'],
                name=data['name'],
                redirect_uri=data['redirect_uri']
            )
            if success:
                return jsonify({"message": message})
        
        elif request.method == 'DELETE':
            client_id = request.args.get('client_id')
            success, message, _ = UserInformation.manage_oauth_client(
                'delete',
                client_id=client_id
            )
            if success:
                return jsonify({"message": message})
        
        return jsonify({"error": message}), 400
        
    except Exception as e:
        logging.error(f"OAuth客户端操作失败: {e}")
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
                user_list = UserInformation.get_user_list()
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
app.register_blueprint(oauth_bp)

# 配置CORS
CORS(app, resources={
    r"/oauth/*": {"origins": OAuthConfig.ALLOWED_ORIGINS},
    r"/api/*": {"origins": OAuthConfig.ALLOWED_ORIGINS}
})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # 应用启动时调用
        
        # 注册示例客户端（仅用于开发测试）
        if not OAuthConfig.REGISTERED_CLIENTS:
            OAuthConfig.register_client(
                client_id="example_client",
                name="示例客户端",
                redirect_uris=["http://localhost:3000/callback"],
                client_secret="example_secret"
            )
            print("已注册示例客户端")
            
    app.run(debug=True)