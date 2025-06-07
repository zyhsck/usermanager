from typing import Dict, Optional, Tuple, Union
import jwt
import time
from datetime import datetime, timedelta
from .UserInformation import UserInformation
from .oauth_models import OAuthClient
from .Config import get_config

class TokenError(Exception):
    """Token相关错误的基类"""
    pass

class InvalidTokenError(TokenError):
    """无效的Token"""
    pass

class ExpiredTokenError(TokenError):
    """Token已过期"""
    pass

class InvalidClientError(TokenError):
    """无效的客户端"""
    pass

class TokenManager:
    """Token管理器，处理JWT令牌的生成、验证和刷新"""
    
    @classmethod
    def _get_config(cls) -> Dict:
        """获取OAuth配置"""
        config = get_config()
        return {
            'token_expiration': config.OAUTH_TOKEN_EXPIRES.total_seconds(),
            'refresh_token_expiration': config.OAUTH_REFRESH_TOKEN_EXPIRES.total_seconds(),
            'token_length': config.OAUTH_TOKEN_LENGTH
        }

    @classmethod
    def generate_token(
        cls, 
        username: str, 
        client_id: str,
        include_refresh_token: bool = True
    ) -> Union[str, Tuple[str, str]]:
        """
        生成JWT访问令牌，可选生成刷新令牌
        
        Args:
            username: 用户名
            client_id: OAuth客户端ID
            include_refresh_token: 是否同时生成刷新令牌
            
        Returns:
            如果include_refresh_token为True，返回(access_token, refresh_token)
            否则只返回access_token
            
        Raises:
            ValueError: 用户不存在
            InvalidClientError: 客户端ID无效
        """
        # 验证用户
        user_info = UserInformation.get_user_info(username)
        if not user_info:
            raise ValueError("用户不存在")
        
        # 验证客户端
        client = OAuthClient.get_client(client_id)
        if not client:
            raise InvalidClientError("无效的客户端ID")
        
        # 获取配置
        config = cls._get_config()
        now = int(time.time())
        
        # 生成访问令牌
        access_payload = {
            'type': 'access',
            'username': username,
            'vip': user_info.get('vip', False),
            'admin': user_info.get('admin', False),
            'client_id': client_id,
            'exp': now + int(config['token_expiration']),
            'iat': now
        }
        
        access_token = jwt.encode(
            access_payload,
            client.client_secret,
            algorithm='HS256'
        )
        
        if not include_refresh_token:
            return access_token
            
        # 生成刷新令牌
        refresh_payload = {
            'type': 'refresh',
            'username': username,
            'client_id': client_id,
            'exp': now + int(config['refresh_token_expiration']),
            'iat': now
        }
        
        refresh_token = jwt.encode(
            refresh_payload,
            client.client_secret,
            algorithm='HS256'
        )
        
        return access_token, refresh_token
    
    @classmethod
    def verify_token(
        cls,
        token: str,
        verify_type: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict]]:
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌
            verify_type: 可选的令牌类型验证('access'或'refresh')
            
        Returns:
            Tuple[bool, Optional[Dict]]: (是否有效, 令牌信息)
            
        Raises:
            InvalidTokenError: 令牌格式无效
            ExpiredTokenError: 令牌已过期
            InvalidClientError: 客户端无效
        """
        try:
            # 先尝试解码令牌以获取client_id（不验证签名）
            try:
                unverified_payload = jwt.decode(
                    token,
                    options={"verify_signature": False}
                )
                client_id = unverified_payload.get('client_id')
                if not client_id:
                    raise InvalidTokenError("令牌中缺少client_id")
                    
                client = OAuthClient.get_client(client_id)
                if not client:
                    raise InvalidClientError("无效的客户端")
                    
            except jwt.PyJWTError as e:
                raise InvalidTokenError(f"令牌解码失败: {str(e)}")
            
            # 使用客户端密钥验证令牌
            payload = jwt.decode(
                token,
                client.client_secret,
                algorithms=['HS256']
            )
            
            # 验证令牌类型
            if verify_type and payload.get('type') != verify_type:
                raise InvalidTokenError(f"令牌类型不匹配，期望{verify_type}")
            
            # 检查令牌是否过期
            if payload.get('exp', 0) < time.time():
                raise ExpiredTokenError("令牌已过期")
            
            # 验证用户是否存在
            username = payload.get('username')
            if not username:
                raise InvalidTokenError("令牌中缺少username")
                
            user_info = UserInformation.get_user_info(username)
            if not user_info:
                raise InvalidTokenError("用户不存在")
            
            # 返回令牌信息
            return True, {
                'type': payload.get('type', 'access'),
                'username': username,
                'vip': user_info.get('vip', False),
                'admin': user_info.get('admin', False),
                'client_id': client_id,
                'exp': datetime.fromtimestamp(payload['exp']),
                'iat': datetime.fromtimestamp(payload['iat'])
            }
            
        except (InvalidTokenError, ExpiredTokenError, InvalidClientError):
            raise
        except jwt.PyJWTError as e:
            raise InvalidTokenError(f"令牌验证失败: {str(e)}")
    
    @classmethod
    def refresh_token(cls, refresh_token: str) -> str:
        """
        使用刷新令牌获取新的访问令牌
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            str: 新的访问令牌
            
        Raises:
            InvalidTokenError: 刷新令牌无效
            ExpiredTokenError: 刷新令牌已过期
            InvalidClientError: 客户端无效
        """
        # 验证刷新令牌
        try:
            valid, token_info = cls.verify_token(refresh_token, verify_type='refresh')
            if not valid or not token_info:
                raise InvalidTokenError("无效的刷新令牌")
        except ExpiredTokenError:
            raise ExpiredTokenError("刷新令牌已过期")
        
        # 生成新的访问令牌
        return cls.generate_token(
            token_info['username'],
            token_info['client_id'],
            include_refresh_token=False
        )
    
    @classmethod
    def revoke_token(cls, token: str) -> bool:
        """
        撤销令牌（可选实现，需要令牌黑名单支持）
        
        Args:
            token: 要撤销的令牌
            
        Returns:
            bool: 撤销是否成功
        """
        # TODO: 实现令牌撤销逻辑，需要Redis支持
        raise NotImplementedError("令牌撤销功能尚未实现")