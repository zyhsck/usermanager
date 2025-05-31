from flask import Blueprint, request, jsonify, redirect, session
from functools import wraps
from .oauth_config import OAuthConfig
from .token_manager import TokenManager
from .UserInformation import UserInformation
from .oauth_models import OAuthClient
from flask_cors import cross_origin
import urllib.parse

oauth_bp = Blueprint('oauth', __name__)

def require_client_auth(f):
    """验证客户端认证的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        client_id = request.headers.get('Client-ID')
        client_secret = request.headers.get('Client-Secret')
        
        if not client_id or not client_secret:
            return jsonify({
                'success': False,
                'message': '缺少客户端认证信息'
            }), 401
            
        client = OAuthClient.get_client(client_id)
        if not client or client.client_secret != client_secret:
            return jsonify({
                'success': False,
                'message': '客户端认证失败'
            }), 401
            
        return f(*args, **kwargs)
    return decorated

@oauth_bp.route('/oauth/authorize')
def authorize():
    """
    授权端点
    接收参数：
    - client_id: 客户端ID
    - redirect_uri: 重定向URI
    - state: 可选的状态参数
    """
    client_id = request.args.get('client_id')
    redirect_uri = request.args.get('redirect_uri')
    state = request.args.get('state', '')
    
    # 验证客户端和重定向URI
    if not client_id or not redirect_uri:
        return jsonify({
            'success': False,
            'message': '缺少必要参数'
        }), 400
        
    client = OAuthClient.get_client(client_id)
    if not client or not client.validate_redirect_uri(redirect_uri):
        return jsonify({
            'success': False,
            'message': '无效的重定向URI'
        }), 400
    
    # 存储认证信息到会话
    session['oauth_client_id'] = client_id
    session['oauth_redirect_uri'] = redirect_uri
    session['oauth_state'] = state
    
    # 如果用户已登录，直接重定向到回调地址
    if 'username' in session:
        token = TokenManager.generate_token(session['username'], client_id)
        return_uri = add_params_to_url(redirect_uri, {
            'token': token,
            'state': state
        })
        return redirect(return_uri)
    
    # 否则重定向到登录页面
    return redirect('/login?oauth=1')

@oauth_bp.route('/oauth/token', methods=['POST'])
@cross_origin()
@require_client_auth
def get_token():
    """
    获取访问令牌
    请求体参数：
    - grant_type: 授权类型（password或refresh_token）
    - username: 用户名（grant_type为password时必需）
    - password: 密码（grant_type为password时必需）
    - refresh_token: 刷新令牌（grant_type为refresh_token时必需）
    """
    grant_type = request.json.get('grant_type')
    client_id = request.headers.get('Client-ID')
    
    if grant_type == 'password':
        username = request.json.get('username')
        password = request.json.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': '缺少用户名或密码'
            }), 400
            
        if not UserInformation.verify_password(username, password):
            return jsonify({
                'success': False,
                'message': '用户名或密码错误'
            }), 401
            
        token = TokenManager.generate_token(username, client_id)
        
        return jsonify({
            'success': True,
            'access_token': token,
            'token_type': 'Bearer',
            'expires_in': OAuthConfig.TOKEN_EXPIRATION
        })
        
    elif grant_type == 'refresh_token':
        refresh_token = request.json.get('refresh_token')
        if not refresh_token:
            return jsonify({
                'success': False,
                'message': '缺少刷新令牌'
            }), 400
            
        new_token = TokenManager.refresh_token(refresh_token)
        if not new_token:
            return jsonify({
                'success': False,
                'message': '无效的刷新令牌'
            }), 401
            
        return jsonify({
            'success': True,
            'access_token': new_token,
            'token_type': 'Bearer',
            'expires_in': OAuthConfig.TOKEN_EXPIRATION
        })
        
    return jsonify({
        'success': False,
        'message': '不支持的授权类型'
    }), 400

@oauth_bp.route('/oauth/verify', methods=['POST'])
@cross_origin()
@require_client_auth
def verify_token():
    """验证令牌"""
    token = request.json.get('token')
    if not token:
        return jsonify({
            'success': False,
            'message': '缺少令牌'
        }), 400
        
    valid, user_info = TokenManager.verify_token(token)
    if not valid:
        return jsonify({
            'success': False,
            'message': '无效的令牌'
        }), 401
        
    return jsonify({
        'success': True,
        'user': user_info
    })

def add_params_to_url(url: str, params: dict) -> str:
    """向URL添加查询参数"""
    url_parts = list(urllib.parse.urlparse(url))
    query = dict(urllib.parse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib.parse.urlencode(query)
    return urllib.parse.urlunparse(url_parts)