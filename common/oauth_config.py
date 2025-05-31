from typing import Dict, List
import os

class OAuthConfig:
    # 允许的客户端域名列表
    ALLOWED_ORIGINS: List[str] = []
    
    # 令牌过期时间（秒）
    TOKEN_EXPIRATION: int = 3600
    
    # 令牌密钥
    TOKEN_SECRET: str = os.environ.get('TOKEN_SECRET', 'your-secret-key')
    
    # 已注册的客户端
    REGISTERED_CLIENTS: Dict[str, Dict] = {
        # 'client_id': {
        #     'name': 'Client Name',
        #     'allowed_redirect_uris': ['https://example.com/callback'],
        #     'client_secret': 'client-secret'
        # }
    }
    
    @classmethod
    def register_client(cls, client_id: str, name: str, redirect_uris: List[str], client_secret: str) -> None:
        """注册新的客户端"""
        cls.REGISTERED_CLIENTS[client_id] = {
            'name': name,
            'allowed_redirect_uris': redirect_uris,
            'client_secret': client_secret
        }
        
        # 添加允许的域名
        for uri in redirect_uris:
            from urllib.parse import urlparse
            domain = f"{urlparse(uri).scheme}://{urlparse(uri).netloc}"
            if domain not in cls.ALLOWED_ORIGINS:
                cls.ALLOWED_ORIGINS.append(domain)
    
    @classmethod
    def validate_redirect_uri(cls, client_id: str, redirect_uri: str) -> bool:
        """验证重定向URI是否合法"""
        if client_id not in cls.REGISTERED_CLIENTS:
            return False
        return redirect_uri in cls.REGISTERED_CLIENTS[client_id]['allowed_redirect_uris']
    
    @classmethod
    def get_client(cls, client_id: str) -> Dict:
        """获取客户端信息"""
        return cls.REGISTERED_CLIENTS.get(client_id)