import json
import os
from pathlib import Path

class ServerConfig:
    """服务器配置管理类，负责读写服务器配置JSON文件"""
    
    CONFIG_FILE = 'server_config.json'
    DEFAULT_CONFIG = {
        'server_name': '用户管理系统',
        'allow_registration': True,
        'max_users': 1000,
        'session_timeout': 3600,
        'log_level': 'info',
        'maintenance_mode': False,
        'maintenance_message': '系统正在维护中，请稍后再试',
        'smtp_settings': {
            'enabled': False,
            'server': '',
            'port': 587,
            'username': '',
            'password': '',
            'use_tls': True,
            'from_email': ''
        }
    }
    
    @classmethod
    def get_config_path(cls):
        """获取配置文件路径"""
        base_dir = Path(__file__).parent.parent
        return os.path.join(base_dir, cls.CONFIG_FILE)
    
    @classmethod
    def load_config(cls):
        """加载服务器配置"""
        config_path = cls.get_config_path()
        
        # 如果配置文件不存在，创建默认配置
        if not os.path.exists(config_path):
            cls.save_config(cls.DEFAULT_CONFIG)
            return cls.DEFAULT_CONFIG.copy()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 确保所有默认配置项都存在
            for key, value in cls.DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
                elif isinstance(value, dict) and isinstance(config[key], dict):
                    # 处理嵌套字典
                    for sub_key, sub_value in value.items():
                        if sub_key not in config[key]:
                            config[key][sub_key] = sub_value
            
            return config
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return cls.DEFAULT_CONFIG.copy()
    
    @classmethod
    def save_config(cls, config):
        """保存服务器配置"""
        config_path = cls.get_config_path()
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    @classmethod
    def update_config(cls, updates):
        """更新部分配置"""
        config = cls.load_config()
        
        # 递归更新配置
        def update_dict(target, source):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    update_dict(target[key], value)
                else:
                    target[key] = value
        
        update_dict(config, updates)
        return cls.save_config(config)