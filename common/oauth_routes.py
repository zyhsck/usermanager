from flask import Blueprint, request, jsonify, redirect, session, current_app
from functools import wraps
from typing import Dict, Optional, Tuple, Any, Callable
from .token_manager import TokenManager, TokenError
from .UserInformation import UserInformation
from .oauth_models import OAuthClient
from .Config import get_config
from flask_cors import cross_origin
import urllib.parse
import logging
from datetime import datetime

oauth_bp = Blueprint('oauth', __name__)

def require_client_auth(f: Callable) -> Callable:
    """
    验证客户端认证的装饰器
    
    Args:
        f: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Tuple[Dict, int]:
        client_id = request.headers.get('Client-ID')
        client_secret = request.headers.get('Client-Secret')
        
        if not client_id or not client_secret:
            return jsonify({
                'success': False,
                'error': 'invalid_request',
                'message': '缺少客户端认证信息'
            }), 401
            
        client = OAuthClient.get_client(client_id)
        if not client or client.client_secret != client_secret:
            return jsonify({
                'success': False,
                'error': 'invalid_client',
                'message': '客户端认证失败'
            }), 401
            
        # 将client对象添加到请求上下文
        request.oauth_client = client
        return f(*args, **kwargs)
    return decorated

def validate_redirect_uri(client: OAuthClient, redirect_uri: str) -> Optional[str]:
    """
    验证重定向URI的有效性和安全性
    
    Args:
        client: OAuth客户端实例
        redirect_uri: 要验证的重定向URI
        
    Returns:
        str: 错误消息，如果验证通过则返回None
    """
    if not redirect_uri:
        return '缺少重定向URI'
        
    if not client.validate_redirect_uri(redirect_uri):
        return '无效的重定向URI'
        
    # 检查URI的安全性
    parsed = urllib.parse.urlparse(redirect_uri)
    if not parsed.scheme or not parsed.netloc:
        return '无效的URI格式'
        
    if parsed.scheme not in ['http', 'https']:
        return '重定向URI必须使用HTTP(S)协议'
    
    return None

@oauth_bp.route('/oauth/authorize')
def authorize() -> Any:
    """
    OAuth2授权端点
    
    Query参数：
    - client_id: 客户端ID
    - redirect_uri: 重定向URI
    - state: 可选的状态参数
    - response_type: 响应类型（目前仅支持'token'）
    
    Returns:
        重定向响应
    """
    client_id = request.args.get('client_id')
    redirect_uri = request.args.get('redirect_uri')
    state = request.args.get('state', '')
    response_type = request.args.get('response_type')
    
    # 基本参数验证
    if not client_id:
        return jsonify({
            'success': False,
            'error': 'invalid_request',
            'message': '缺少client_id参数'
        }), 400
        
    if response_type != 'token':
        return jsonify({
            'success': False,
            'error': 'unsupported_response_type',
            'message': '不支持的response_type'
        }), 400
        
    # 验证客户端
    client = OAuthClient.get_client(client_id)
    if not client:
        return jsonify({
            'success': False,
            'error': 'invalid_client',
            'message': '无效的客户端ID'
        }), 400
        
    # 验证重定向URI
    error = validate_redirect_uri(client, redirect_uri)
    if error:
        return jsonify({
            'success': False,
            'error': 'invalid_redirect_uri',
            'message': error
        }), 400
    
    # 存储认证信息到会话
    session['oauth_client_id'] = client_id
    session['oauth_redirect_uri'] = redirect_uri
    session['oauth_state'] = state
    
    # 如果用户已登录，直接授权
    if session.get('IsLogin') and session.get('username'):
        try:
            access_token, refresh_token = TokenManager.generate_token(
                session['username'],
                client_id,
                include_refresh_token=True
            )
            
            return_uri = add_params_to_url(redirect_uri, {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': int(get_config().OAUTH_TOKEN_EXPIRES.total_seconds()),
                'state': state
            })
            
            # 记录授权日志
            logging.info(
                f"OAuth授权成功 - 用户: {session['username']}, "
                f"客户端: {client.name} ({client_id})"
            )
            
            return redirect(return_uri)
            
        except Exception as e:
            logging.error(f"OAuth授权失败: {str(e)}")
            error_uri = add_params_to_url(redirect_uri, {
                'error': 'server_error',
                'error_description': '服务器内部错误',
                'state': state
            })
            return redirect(error_uri)
    
    # 未登录则重定向到登录页面
    return redirect('/login?oauth=1')

@oauth_bp.route('/oauth/token', methods=['POST'])
@cross_origin()
@require_client_auth
def get_token() -> Tuple[Dict, int]:
    """
    OAuth2令牌端点
    
    请求体参数：
    - grant_type: 授权类型（password或refresh_token）
    - username: 用户名（grant_type为password时必需）
    - password: 密码（grant_type为password时必需）
    - refresh_token: 刷新令牌（grant_type为refresh_token时必需）
    
    Returns:
        JSON响应
    """
    try:
        grant_type = request.json.get('grant_type')
        client = request.oauth_client
        
        if grant_type == 'password':
            username = request.json.get('username')
            password = request.json.get('password')
            
            if not username or not password:
                return jsonify({
                    'success': False,
                    'error': 'invalid_request',
                    'message': '缺少用户名或密码'
                }), 400
                
            if not UserInformation.verify_password(username, password):
                return jsonify({
                    'success': False,
                    'error': 'invalid_grant',
                    'message': '用户名或密码错误'
                }), 401
                
            access_token, refresh_token = TokenManager.generate_token(
                username,
                client.client_id,
                include_refresh_token=True
            )
            
        elif grant_type == 'refresh_token':
            refresh_token = request.json.get('refresh_token')
            if not refresh_token:
                return jsonify({
                    'success': False,
                    'error': 'invalid_request',
                    'message': '缺少刷新令牌'
                }), 400
                
            try:
                access_token = TokenManager.refresh_token(refresh_token)
                refresh_token = None  # 不返回新的刷新令牌
            except TokenError as e:
                return jsonify({
                    'success': False,
                    'error': 'invalid_grant',
                    'message': str(e)
                }), 401
                
        else:
            return jsonify({
                'success': False,
                'error': 'unsupported_grant_type',
                'message': '不支持的授权类型'
            }), 400
            
        response = {
            'success': True,
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': int(get_config().OAUTH_TOKEN_EXPIRES.total_seconds())
        }
        
        if refresh_token:
            response['refresh_token'] = refresh_token
            
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"令牌端点错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': '服务器内部错误'
        }), 500

@oauth_bp.route('/oauth/verify', methods=['POST'])
@cross_origin()
@require_client_auth
def verify_token() -> Tuple[Dict, int]:
    """
    验证令牌端点
    
    请求体参数：
    - token: 要验证的访问令牌
    
    Returns:
        JSON响应，包含令牌信息或错误消息
    """
    try:
        token = request.json.get('token')
        if not token:
            return jsonify({
                'success': False,
                'error': 'invalid_request',
                'message': '缺少令牌'
            }), 400
            
        valid, token_info = TokenManager.verify_token(token)
        if not valid or not token_info:
            return jsonify({
                'success': False,
                'error': 'invalid_token',
                'message': '无效的令牌'
            }), 401
            
        # 确保令牌属于当前客户端
        if token_info['client_id'] != request.oauth_client.client_id:
            return jsonify({
                'success': False,
                'error': 'invalid_token',
                'message': '令牌不属于此客户端'
            }), 401
            
        # 转换datetime对象为ISO格式字符串
        token_info['exp'] = token_info['exp'].isoformat()
        token_info['iat'] = token_info['iat'].isoformat()
            
        return jsonify({
            'success': True,
            'token_info': token_info
        })
        
    except TokenError as e:
        return jsonify({
            'success': False,
            'error': 'invalid_token',
            'message': str(e)
        }), 401
        
    except Exception as e:
        logging.error(f"令牌验证错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': '服务器内部错误'
        }), 500

def add_params_to_url(url: str, params: Dict[str, Any]) -> str:
    """
    向URL添加查询参数
    
    Args:
        url: 原始URL
        params: 要添加的参数字典
        
    Returns:
        str: 添加参数后的URL
    """
    url_parts = list(urllib.parse.urlparse(url))
    query = dict(urllib.parse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib.parse.urlencode(query)
    return urllib.parse.urlunparse(url_parts)