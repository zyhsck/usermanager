# common模块初始化文件
from .db_instance import db
from .db_setup import init_db

__all__ = ['db', 'init_db']