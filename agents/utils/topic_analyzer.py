import logging
import jieba
import numpy as np
from gensim.models import KeyedVectors
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class TopicAnalyzer:
    def __init__(self, model_path: Optional[str] = None):
        """
        初始化主题分析器
        
        Args:
            model_path: Word2Vec模型路径，如果为None则使用默认模型
        """
        self.word_vectors = None
        try:
            if model_path:
                self.word_vectors = KeyedVectors.load_word2vec_format(model_path, binary=True)
            else:
                # 使用默认的中文词向量模型
                default_model = "models/sgns.weibo.bigram"
                self.word_vectors = KeyedVectors.load_word2vec_format(default_model, binary=True)
        except Exception as e:
            logger.error(f"加载词向量模型失败: {str(e)}")
    
    def get_text_vector(self, text: str) -> np.ndarray:
        """
        获取文本的向量表示
        
        Args:
            text: 输入文本
            
        Returns:
            文本的向量表示
        """
        if not self.word_vectors:
            return np.zeros(300)  # 默认向量维度
            
        words = jieba.lcut(text)
        vectors = []
        
        for word in words:
            try:
                if word in self.word_vectors:
                    vectors.append(self.word_vectors[word])
            except Exception as e:
                logger.debug(f"获取词向量失败: {word}")
                continue
                
        if not vectors:
            return np.zeros(self.word_vectors.vector_size)
            
        return np.mean(vectors, axis=0)
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的主题相似度
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
            
        Returns:
            相似度得分 (0.0 到 1.0)
        """
        try:
            vec1 = self.get_text_vector(text1)
            vec2 = self.get_text_vector(text2)
            
            # 计算余弦相似度
            similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
            return float(max(0.0, min(1.0, similarity)))  # 确保结果在[0,1]范围内
            
        except Exception as e:
            logger.error(f"计算文本相似度失败: {str(e)}")
            return 0.0

# 创建全局实例
_analyzer = TopicAnalyzer()

def analyze_topic_similarity(text1: str, text2: str) -> float:
    """
    分析两段文本的主题相似度
    
    Args:
        text1: 第一段文本
        text2: 第二段文本
        
    Returns:
        相似度得分 (0.0 到 1.0)
    """
    return _analyzer.calculate_similarity(text1, text2) 