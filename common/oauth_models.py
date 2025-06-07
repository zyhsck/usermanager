from .db_setup import db
from datetime import datetime
import json

class OAuthClient(db.Model):
    __bind_key__ = 'oauth_db'
    __tablename__ = 'oauth_clients'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(100), unique=True, nullable=False)
    client_secret = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    redirect_uri = db.Column(db.String(500), nullable=False)
    created_by = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def __init__(self, name, redirect_uri, created_by, client_id=None, client_secret=None):
        from uuid import uuid4
        self.client_id = client_id or str(uuid4())
        self.client_secret = client_secret or str(uuid4())
        self.name = name
        self.created_by = created_by
        self.redirect_uri = redirect_uri
        self.is_active = True

    def to_dict(self):
        """转换为字典格式"""
        return {
            'client_id': self.client_id,
            'name': self.name,
            'redirect_uri': self.redirect_uri,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'created_by': self.created_by
        }

    @staticmethod
    def create_client(name, redirect_uri, created_by):
        """创建新的OAuth客户端"""
        client = OAuthClient(name=name, redirect_uri=redirect_uri, created_by=created_by)
        db.session.add(client)
        db.session.commit()
        return client

    @staticmethod
    def get_client(client_id):
        """通过client_id获取客户端"""
        return OAuthClient.query.filter_by(client_id=client_id, is_active=True).first()

    def validate_redirect_uri(self, redirect_uri):
        """验证重定向URI是否合法"""
        return redirect_uri == self.redirect_uri