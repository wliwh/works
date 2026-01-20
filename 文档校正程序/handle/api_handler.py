"""
API调用处理模块
提供重试机制、错误处理和日志记录功能
"""

import time
import logging
import os
from typing import Optional, Dict, Any, List
from openai import OpenAI
from openai import APIError, RateLimitError, APIConnectionError

class Config:
    """配置管理类"""
    
    # API配置
    ARK_CONFIG = {
        'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
        'api_key': '91971d49-2bf9-45e9-92d7-80c88f178500',  # 建议从环境变量读取
        'max_retries': 1,
        'retry_delay': 2.0,
        'timeout': 60
    }
    
    OLLAMA_CONFIG = {
        'base_url': 'http://localhost:11434/v1',
        'api_key': 'ollama',
        'max_retries': 1,
        'retry_delay': 1.0,
        'timeout': 120
    }
    
    # 日志配置
    LOG_CONFIG = {
        'level': 'WARNING',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': 'api_calls.log',
        'max_size': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5
    }
    
    @classmethod
    def get_ark_config(cls) -> Dict[str, Any]:
        """获取ARK API配置"""
        config = cls.ARK_CONFIG.copy()
        # 优先从环境变量读取API密钥
        api_key = os.getenv('ARK_API_KEY')
        if api_key:
            config['api_key'] = api_key
        return config
    
    @classmethod
    def get_ollama_config(cls) -> Dict[str, Any]:
        """获取Ollama API配置"""
        return cls.OLLAMA_CONFIG.copy()
    
    @classmethod
    def get_log_config(cls) -> Dict[str, Any]:
        """获取日志配置"""
        return cls.LOG_CONFIG.copy()


# 配置日志
def setup_logging():
    """设置日志配置"""
    log_config = Config.get_log_config()
    
    # 创建日志目录
    log_dir = os.path.dirname(log_config['file'])
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, log_config['level']),
        format=log_config['format'],
        handlers=[
            logging.FileHandler(log_config['file'], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

# 初始化日志
setup_logging()
logger = logging.getLogger(__name__)


class APIHandler:
    """API调用处理器，提供重试机制和错误处理"""
    
    def __init__(self, 
                 base_url: str, 
                 api_key: str,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 timeout: int = 30):
        """
        初始化API处理器
        
        Args:
            base_url: API基础URL
            api_key: API密钥
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url
        self.api_key = api_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout
        )
        
        logger.info(f"API处理器初始化完成 - URL: {base_url}")
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """判断错误是否可重试"""
        if isinstance(error, (APIConnectionError, RateLimitError)):
            return True
        if isinstance(error, APIError):
            # 5xx错误通常可以重试
            return hasattr(error, 'status_code') and error.status_code >= 500
        return False
    
    def _wait_for_retry(self, attempt: int):
        """等待重试"""
        delay = self.retry_delay * (2 ** (attempt - 1))  # 指数退避
        logger.warning(f"等待 {delay:.1f} 秒后重试 (第 {attempt} 次尝试)")
        time.sleep(delay)
    
    def chat_completion(self,
                       messages: List[Dict[str, str]],
                       model: str,
                       **kwargs) -> Optional[str]:
        """
        带重试机制的聊天完成API调用
        
        Args:
            messages: 消息列表
            model: 模型名称
            **kwargs: 其他参数
            
        Returns:
            响应文本或None（如果所有重试都失败）
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"开始API调用 (第 {attempt} 次尝试) - 模型: {model}")
                
                # 创建流式响应
                stream = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    **kwargs)
                
                # 收集响应
                result = []
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        result.append(chunk.choices[0].delta.content)
                
                response_text = ''.join(result)
                logger.info(f"API调用成功，响应长度: {len(response_text)}")
                return response_text
                
            except RateLimitError as e:
                logger.error(f"API速率限制: {e}")
                last_error = e
                if self._is_retryable_error(e) and attempt < self.max_retries:
                    self._wait_for_retry(attempt)
                    continue
                    
            except APIConnectionError as e:
                logger.error(f"API连接错误: {e}")
                last_error = e
                if self._is_retryable_error(e) and attempt < self.max_retries:
                    self._wait_for_retry(attempt)
                    continue
                    
            except APIError as e:
                logger.error(f"API错误: {e}")
                last_error = e
                if self._is_retryable_error(e) and attempt < self.max_retries:
                    self._wait_for_retry(attempt)
                    continue
                    
            except Exception as e:
                logger.error(f"未知错误: {e}")
                last_error = e
                break
        
        logger.error(f"API调用失败，已达到最大重试次数: {last_error}")
        return None
    
    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            logger.info("测试API连接...")
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo" if "openai" in self.base_url else "gpt-oss:latest",
                messages=[{"role": "user", "content": "测试连接"}],
                max_tokens=10
            )
            logger.info("API连接测试成功")
            return True
        except Exception as e:
            logger.error(f"API连接测试失败: {e}")
            return False


class APIConfig:
    """API配置管理"""
    
    @staticmethod
    def get_ark_config() -> Dict[str, Any]:
        """获取ARK API配置"""
        return Config.get_ark_config()
    
    @staticmethod
    def get_ollama_config() -> Dict[str, Any]:
        """获取Ollama API配置"""
        return Config.get_ollama_config()


def create_api_handler(api_type: str = 'ark') -> APIHandler:
    """
    创建API处理器实例
    
    Args:
        api_type: API类型 ('ark' 或 'ollama')
        
    Returns:
        APIHandler实例
    """
    if api_type == 'ark':
        config = APIConfig.get_ark_config()
    elif api_type == 'ollama':
        config = APIConfig.get_ollama_config()
    else:
        raise ValueError(f"不支持的API类型: {api_type}")
    
    return APIHandler(**config)
