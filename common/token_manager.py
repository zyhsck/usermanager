import jwt
import time
from typing import Dict, Optional, Tuple
from .UserInformation import UserInformation
from .oauth_models import OAuthClient

# 默认令牌过期时间（24小时）
DEFAULT_TOKEN_EXPIRATION = 24 * 60 * 60
# 默认令牌密钥
DEFAULT_TOKEN_SECRET = 'your-secret-key'

class TokenManager:
    @staticmethod
    def generate_token(username: str, client_id: str) -> str:
        """
        生成JWT令牌
        
        Args:
            username: 用户名
            client_id: 客户端ID
            
        Returns:
            str: JWT令牌
        """
        user_info = UserInformation.get_user_info(username)
        if not user_info:
            raise ValueError("用户不存在")
        
        # 获取客户端配置
        client = OAuthClient.get_client(client_id)
        if not client:
            raise ValueError("无效的客户端ID")
            
        # 使用客户端配置的过期时间，如果没有则使用默认值
        token_expiration = getattr(client, 'token_expiration', DEFAULT_TOKEN_EXPIRATION)
        token_secret = getattr(client, 'token_secret', DEFAULT_TOKEN_SECRET)
        
        payload = {
            'username': username,
            'vip': user_info.get('vip', False),
            'admin': user_info.get('admin', False),
            'client_id': client_id,
            'exp': int(time.time()) + token_expiration,
            'iat': int(time.time())
        }
        
        return jwt.encode(payload, token_secret, algorithm='HS256')
    
    @staticmethod
    def verify_token(token: str) -> Tuple[bool, Optional[Dict]]:
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌
            
        Returns:
            Tuple[bool, Optional[Dict]]: (是否有效, 用户信息)
        """
        try:
            # 先尝试解码令牌以获取client_id
            try:
                unverified_payload = jwt.decode(token, options={"verify_signature": False})
                client_id = unverified_payload.get('client_id')
                client = OAuthClient.get_client(client_id) if client_id else None
                token_secret = getattr(client, 'token_secret', DEFAULT_TOKEN_SECRET)
            except jwt.PyJWTError:
                return False, None
            
            # 使用正确的密钥验证令牌
            payload = jwt.decode(token, token_secret, algorithms=['HS256'])
            
            # 检查令牌是否过期
            if payload.get('exp', 0) < time.time():
                return False, None
            
            # 验证用户是否存在
            username = payload.get('username')
            user_info = UserInformation.get_user_info(username)
            if not user_info:
                return False, None
            
            # 返回用户信息
            return True, {
                'username': username,
                'vip': user_info.get('vip', False),
                'admin': user_info.get('admin', False),
                'client_id': payload.get('client_id')
            }
        except jwt.PyJWTError:
            return False, None
    
    @staticmethod
    def refresh_token(token: str) -> Optional[str]:
        """
        刷新令牌
        
        Args:
            token: 原JWT令牌
            
        Returns:
            Optional[str]: 新的JWT令牌，如果原令牌无效则返回None
        """
        valid, user_info = TokenManager.verify_token(token)
        if not valid or not user_info:
            return None
        
        return TokenManager.generate_token(
            user_info['username'], 
            user_info['client_id']
        )