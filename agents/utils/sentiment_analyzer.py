"""
简单的情绪分析工具

使用词典匹配的方式分析文本的情感倾向。
实际生产环境中可替换为更高级的NLP服务或模型。
"""

import re
import jieba
import logging
from textblob import TextBlob
from typing import Union, Dict, Any

logger = logging.getLogger(__name__)

# 情感词典
POSITIVE_WORDS = {
    'zh': [
        '好', '棒', '喜欢', '满意', '开心', '高兴', '成功', '欢迎', '优秀', '漂亮',
        '精彩', '完美', '表扬', '感谢', '欣赏', '赞', '美', '佳', '优', '嗯', '是的',
        '对', '爱', '喜欢', '支持', '好用', '方便', '实用', '强大', '帮助'
    ],
    'en': [
        'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'happy',
        'thank', 'thanks', 'love', 'like', 'nice', 'well', 'perfect', 'yes', 'awesome',
        'cool', 'helpful', 'impressive', 'beautiful', 'brilliant', 'enjoy', 'satisfied'
    ]
}

NEGATIVE_WORDS = {
    'zh': [
        '不', '差', '糟', '坏', '失望', '难过', '失败', '讨厌', '错误', '缺陷',
        '问题', '弱', '慢', '复杂', '困难', '麻烦', '生气', '遗憾', '可惜', '不好',
        '不行', '无法', '不能', '不会', '讨厌', '厌倦', '不满', '怀疑', '担心', '害怕'
    ],
    'en': [
        'bad', 'poor', 'terrible', 'awful', 'horrible', 'sad', 'fail', 'hate',
        'error', 'bug', 'issue', 'problem', 'slow', 'difficult', 'hard', 'wrong',
        'angry', 'annoyed', 'dislike', 'disappointed', 'no', 'not', 'never', 'cannot',
        'ugly', 'useless', 'worse', 'worst', 'fear', 'worried'
    ]
}

# 强度修饰词
INTENSIFIERS = {
    'zh': {
        '非常': 2.0, '特别': 2.0, '十分': 2.0, '极其': 2.5, '超级': 2.5,
        '有点': 0.5, '稍微': 0.5, '略微': 0.5, '有些': 0.7, '太': 2.0,
        '格外': 2.0, '尤其': 2.0, '颇为': 1.5, '分外': 1.8, '异常': 2.0
    },
    'en': {
        'very': 2.0, 'extremely': 2.5, 'incredibly': 2.5, 'really': 1.8,
        'so': 1.5, 'too': 1.5, 'absolutely': 2.5, 'completely': 2.0,
        'quite': 1.3, 'somewhat': 0.7, 'slightly': 0.5, 'a bit': 0.5,
        'rather': 1.2, 'pretty': 1.4, 'fairly': 1.2, 'highly': 1.8
    }
}

# 反转词
NEGATIONS = {
    'zh': ['不', '没', '没有', '不是', '不会', '不能', '不要', '不可', '绝不', '否'],
    'en': ['not', 'no', 'never', 'none', 'neither', 'nor', "don't", "doesn't", "didn't", "can't", "won't"]
}

def detect_language(text):
    """简单检测文本语言类型，返回'zh'或'en'"""
    # 计算中文字符比例
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    if chinese_chars / max(len(text), 1) > 0.1:  # 如果包含超过10%的中文字符
        return 'zh'
    return 'en'  # 默认为英文

def tokenize(text, lang):
    """根据语言分词"""
    if lang == 'zh':
        return list(jieba.cut(text))
    else:  # 英文简单按空格分词
        return re.findall(r'\w+|[^\w\s]', text.lower())

def analyze_sentiment(text, detailed=False):
    """
    分析文本的情感倾向
    
    参数:
    - text: 要分析的文本内容
    - detailed: 是否返回详细信息
    
    返回:
    - 情感得分: 范围从-1到1，正值表示积极，负值表示消极
    - 详细信息(如果detailed=True): 包含分词、得分细节等
    """
    if not text:
        return 0.0
    
    try:
        # 检测语言
        lang = detect_language(text)
        
        # 分词
        tokens = tokenize(text, lang)
        
        # 初始化
        score = 0.0
        detail = {
            'tokens': tokens,
            'matches': []
        }
        
        # 检查每个词的情感
        for i, token in enumerate(tokens):
            # 检查是否是情感词
            multiplier = 1.0
            is_positive = token.lower() in POSITIVE_WORDS[lang]
            is_negative = token.lower() in NEGATIVE_WORDS[lang]
            
            # 检查前面是否有反转词
            if i > 0:
                for j in range(max(0, i-3), i):
                    if tokens[j].lower() in NEGATIONS[lang]:
                        multiplier *= -1
                        if detailed:
                            detail['matches'].append({
                                'token': tokens[j],
                                'type': 'negation',
                                'position': j
                            })
            
            # 检查前面是否有强度修饰词
            if i > 0:
                for j in range(max(0, i-2), i):
                    intensifier = tokens[j].lower()
                    if intensifier in INTENSIFIERS[lang]:
                        multiplier *= INTENSIFIERS[lang][intensifier]
                        if detailed:
                            detail['matches'].append({
                                'token': intensifier,
                                'type': 'intensifier',
                                'position': j,
                                'value': INTENSIFIERS[lang][intensifier]
                            })
            
            # 计算分数
            if is_positive:
                score += 1.0 * multiplier
                if detailed:
                    detail['matches'].append({
                        'token': token,
                        'type': 'positive',
                        'position': i,
                        'contribution': 1.0 * multiplier
                    })
            elif is_negative:
                score -= 1.0 * multiplier
                if detailed:
                    detail['matches'].append({
                        'token': token,
                        'type': 'negative',
                        'position': i,
                        'contribution': -1.0 * multiplier
                    })
        
        # 标准化得分到[-1, 1]范围
        if score != 0:
            normalized_score = max(min(score / (len(tokens) * 0.3), 1.0), -1.0)
        else:
            normalized_score = 0.0
            
        if detailed:
            detail['raw_score'] = score
            detail['normalized_score'] = normalized_score
            return normalized_score, detail
            
        return normalized_score
        
    except Exception as e:
        logger.error(f"情感分析过程出错: {str(e)}", exc_info=True)
        return 0.0  # 出错时返回中性值

class SentimentAnalyzer:
    def __init__(self):
        """初始化情感分析器"""
        pass
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        分析文本的情感
        
        Args:
            text: 要分析的文本
            
        Returns:
            包含情感分析结果的字典:
            {
                'score': float,  # 情感得分 (-1.0 到 1.0)
                'polarity': str,  # 'positive', 'negative', 或 'neutral'
                'confidence': float  # 置信度 (0.0 到 1.0)
            }
        """
        try:
            # 使用TextBlob进行情感分析
            blob = TextBlob(text)
            sentiment = blob.sentiment
            
            # 获取情感极性 (-1.0 到 1.0)
            score = sentiment.polarity
            
            # 获取主观性得分作为置信度 (0.0 到 1.0)
            confidence = sentiment.subjectivity
            
            # 确定情感倾向
            if score > 0.3:
                polarity = 'positive'
            elif score < -0.3:
                polarity = 'negative'
            else:
                polarity = 'neutral'
            
            return {
                'score': score,
                'polarity': polarity,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"情感分析失败: {str(e)}")
            return {
                'score': 0.0,
                'polarity': 'neutral',
                'confidence': 0.0
            }

# 创建全局实例
_analyzer = SentimentAnalyzer()

def analyze_sentiment(text: str) -> float:
    """
    分析文本情感并返回情感得分
    
    Args:
        text: 要分析的文本
        
    Returns:
        情感得分 (-1.0 到 1.0)
    """
    result = _analyzer.analyze(text)
    return result['score'] 