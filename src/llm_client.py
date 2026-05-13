"""
智谱AI GLM-4-Flash 客户端
用于论文筛选、总结和翻译
"""

import requests
import json
import re
from typing import List, Dict, Optional


class GLMClient:
    """智谱AI GLM-4-Flash 客户端"""
    
    def __init__(self, api_key: str, api_url: str):
        """
        初始化GLM客户端
        
        Args:
            api_key: 智谱AI API Key
            api_url: API端点地址
        """
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def chat(self, messages: List[Dict], temperature: float = 0.2, max_tokens: int = 500) -> Optional[str]:
        """
        调用GLM-4-Flash模型
        
        Args:
            messages: 对话消息列表
            temperature: 温度参数（0-1），越低越确定性
            max_tokens: 最大输出token数
            
        Returns:
            模型返回的内容
        """
        payload = {
            "model": "glm-4-flash",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            print(f"❌ GLM API调用失败: {e}")
            return None
        except (KeyError, json.JSONDecodeError) as e:
            print(f"❌ 解析GLM响应失败: {e}")
            return None
    
    def filter_paper(self, title: str, abstract: str, research_area: str) -> Dict:
        """
        判断论文是否与研究领域相关（默认温度0.1，保守模式）
        
        Args:
            title: 论文标题
            abstract: 论文摘要
            research_area: 研究领域描述
            
        Returns:
            {"is_relevant": bool, "reason": str}
        """
        return self.filter_paper_with_temp(title, abstract, research_area, temperature=0.1)

    def filter_paper_with_temp(self, title: str, abstract: str, research_area: str, temperature: float = 0.3) -> Dict:
        """
        优化版：结构化判断 + Few-Shot 示例 + 负向约束 + 相关性评分
        """
        content = abstract if abstract else title

        # 1. System Prompt：设定专家角色与严格判断边界
        system_prompt = """你是资深学术审稿人。请严格根据【判断标准】评估论文相关性。
        【判断标准】：
        1. 方法匹配：核心技术需与关键词强相关（如 GNN、时空预测、遥感解译等）；
        2. 场景匹配：应用领域需落在关键词指定范围（如交通、地理、遥感、城市计算）；
        3. 负向约束：仅标题/摘要中“提及关键词”但无实质方法、模型或实验支撑的，判定为不相关；
        4. 语言兼容：即使论文是其他语言，也请根据实际内容判断。

        【输出格式】：必须为合法 JSON，严禁包含 markdown 代码块标记或其他解释文字。
        {"is_relevant": true/false, "match_score": 0-10整数, "reason": "20字以内中文理由"}
        """

        # 2. Few-Shot 示例：提供 1 正 1 反，大幅对齐判断逻辑
        few_shot_examples = """
        【示例 1 - 相关】
        标题：Traffic Flow Prediction using Graph Neural Networks
        摘要：We propose a spatio-temporal graph convolutional network for urban traffic forecasting.
        关键词：交通流预测，图神经网络
        输出：{"is_relevant": true, "match_score": 9, "reason": "GNN方法+交通场景，高度匹配"}

        【示例 2 - 不相关】
        标题：A Review of Deep Learning in Healthcare
        摘要：This paper surveys deep learning applications in medical image analysis.
        关键词：交通流预测，图神经网络
        输出：{"is_relevant": false, "match_score": 1, "reason": "领域为医疗，完全不相关"}
        """

        # 3. User Prompt：传入待评估内容
        user_prompt = f"""待评估论文：
        标题：{title}
        摘要：{content}
        用户关键词：{research_area}

        请输出 JSON："""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": few_shot_examples},
            {"role": "assistant", "content": "明白，请提供待评估论文。"},
            {"role": "user", "content": user_prompt}
        ]

        # 4. 参数调优：筛选任务求稳，温度上限锁死 0.3，限制 Token 防啰嗦
        response = self.chat(messages, temperature=min(temperature, 0.3), max_tokens=150)

        if response:
            try:
                # 增强容错：清理可能存在的 markdown 符号
                clean_json = re.sub(r'', '', response).strip()
                json_match = re.search(r'\{.*\}', clean_json, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return {
                        "is_relevant": bool(result.get("is_relevant", False)),
                        "reason": str(result.get("reason", "")),
                        "match_score": int(result.get("match_score", 0))
                    }
            except Exception:
                pass

        return {"is_relevant": False, "reason": "解析失败", "match_score": 0}

    def summarize_paper(self, title: str, abstract: str) -> Optional[str]:
        """
        优化版：结构化摘要 + 防幻觉机制 + 保留核心指标
        """
        if not abstract:
            abstract = "无摘要"

        # 优化 Prompt：强制结构化输出，明确禁止编造数据
        prompt = f"""请作为领域专家，将以下论文摘要转化为结构化中文简报。
        【输出格式】：
        【背景】...（1句话）
        【方法】...（核心模型/技术，1-2句话）
        【结论/指标】...（关键结果或数据集，1句话）

        【硬性要求】：
        1. 必须保留关键数据集名称、模型指标（如 Accuracy, RMSE, F1）；
        2. 总字数严格控制在 100 字以内；
        3. 严禁编造原文未提及的数据、结论或方法；
        4. 若原文缺失某项信息，标注“未提及”。

        标题：{title}
        摘要：{abstract}
        """

        messages = [
            {"role": "system", "content": "你是高效的学术信息提取助手，擅长提炼核心贡献。"},
            {"role": "user", "content": prompt}
        ]

        return self.chat(messages, temperature=0.4, max_tokens=300)

    def translate_title(self, title: str) -> Optional[str]:
        """
        优化版：学术化翻译 + 术语一致性
        """
        prompt = f"""请将以下英文学术论文标题翻译为专业流畅的中文。
           【要求】：
           1. 符合计算机/地学领域学术命名习惯；
           2. 专有名词（如模型名、数据集）保留英文或通用译名；
           3. 只输出中文标题，严禁添加任何解释、引号或前缀。

           英文标题：{title}
           中文翻译："""

        messages = [
            {"role": "system", "content": "你是资深学术翻译，擅长 AI 与地学交叉领域术语。"},
            {"role": "user", "content": prompt}
        ]

        return self.chat(messages, temperature=0.2, max_tokens=80)


# 测试代码
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from config.settings import ZHIPU_API_KEY, ZHIPU_API_URL, RESEARCH_AREA

    if not ZHIPU_API_KEY:
        print("❌ 请先在.env文件中配置ZHIPU_API_KEY")
    else:
        client = GLMClient(ZHIPU_API_KEY, ZHIPU_API_URL)

        print("=" * 50)
        print("测试不同温度下的筛选效果")
        print("=" * 50)

        test_title = "Deep Learning for Remote Sensing Image Classification"
        test_abstract = "This paper proposes a novel CNN architecture for land cover classification using satellite imagery."

        # 测试不同温度
        for temp in [0.1, 0.3, 0.5, 0.7]:
            result = client.filter_paper_with_temp(test_title, test_abstract, RESEARCH_AREA, temperature=temp)
            print(f"温度 {temp}: 相关={result['is_relevant']}, 理由={result['reason']}")

        print("\n" + "=" * 40)
        print("测试2：标题翻译")
        print("=" * 40)

        translated = client.translate_title(test_title)
        print(f"翻译结果: {translated}")

        print("\n" + "=" * 40)
        print("测试3：论文总结")
        print("=" * 40)

        summary = client.summarize_paper(test_title, test_abstract)
        print(f"摘要: {summary}")