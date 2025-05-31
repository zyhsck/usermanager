from .Config import db
from datetime import datetime
import json

class OAuthClient(db.Model):
    __bind_key__ = 'oauth_db'
    __tablename__ = 'oauth_clients'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), unique=True, nullable=False)
    client_secret = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    redirect_uris = db.Column(db.Text, nullable=False)  # 存储为JSON字符串
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def __init__(self, name, redirect_uris, client_id=None, client_secret=None):
        from uuid import uuid4
        self.client_id = client_id or str(uuid4())
        self.client_secret = client_secret or str(uuid4())
        self.name = name
        self.set_redirect_uris(redirect_uris)

    def get_redirect_uris(self):
        """获取重定向URI列表"""
        return json.loads(self.redirect_uris)

    def set_redirect_uris(self, uris):
        """设置重定向URI列表"""
        if isinstance(uris, str):
            uris = [uris]
        self.redirect_uris = json.dumps(list(uris))

    def to_dict(self):
        """转换为字典格式"""
        return {
            'client_id': self.client_id,
            'name': self.name,
            'redirect_uris': self.get_redirect_uris(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active
        }

    @staticmethod
    def create_client(name, redirect_uris):
        """创建新的OAuth客户端"""
        client = OAuthClient(name=name, redirect_uris=redirect_uris)
        db.session.add(client)
        db.session.commit()
        return client

    @staticmethod
    def get_client(client_id):
        """通过client_id获取客户端"""
        return OAuthClient.query.filter_by(client_id=client_id, is_active=True).first()

    def validate_redirect_uri(self, redirect_uri):
        """验证重定向URI是否合法"""
        return redirect_uri in self.get_redirect_uris()