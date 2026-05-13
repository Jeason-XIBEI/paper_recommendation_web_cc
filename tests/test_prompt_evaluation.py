"""
Prompt 调优效果自动化评估脚本
"""
import json
import os
import time
from src.llm_client import GLMClient
from config.settings import ZHIPU_API_KEY, ZHIPU_API_URL

def evaluate_prompt_performance():
    # 1. 初始化客户端
    client = GLMClient(ZHIPU_API_KEY, ZHIPU_API_URL)

    # 2. 加载测试集
    try:
        data_path = os.path.join(os.path.dirname(__file__), 'test_data.json')
        with open(data_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
    except FileNotFoundError:
        print("❌ 未找到 test_data.json，请先创建测试集。")
        return

    print("=" * 60)
    print("🚀 开始 Prompt 效果评估")
    print("=" * 60)

    total = len(test_data)
    tp, tn, fp, fn = 0, 0, 0, 0  # 混淆矩阵变量
    errors = []

    for item in test_data:
        print(f"\n📄 测试 ID {item['id']}: {item['title'][:40]}...")

        start_time = time.time()
        # 调用模型（这里用你优化后的函数）
        result = client.filter_paper_with_temp(
            title=item['title'],
            abstract=item['abstract'],
            research_area=item['keywords'],
            temperature=0.3
        )
        end_time = time.time()

        ai_relevant = result.get('is_relevant', False)
        ai_score = result.get('match_score', 0)
        ai_reason = result.get('reason', '')
        latency = end_time - start_time

        true_label = item['expected_relevant']

        # 计算混淆矩阵
        if ai_relevant and true_label:
            tp += 1
        elif not ai_relevant and not true_label:
            tn += 1
        elif ai_relevant and not true_label:
            fp += 1  # 误报 (False Positive)
        elif not ai_relevant and true_label:
            fn += 1  # 漏报 (False Negative)

        # 记录错误案例
        if ai_relevant != true_label:
            errors.append({
                "id": item['id'],
                "title": item['title'],
                "expected": true_label,
                "got": ai_relevant,
                "reason": ai_reason,
                "score": ai_score
            })

        print(f"   ✅ 预期：{'相关' if true_label else '不相关'} | 实际：{'相关' if ai_relevant else '不相关'} (得分:{ai_score}) | 耗时：{latency:.2f}s")
        print(f"   💬 AI 理由：{ai_reason}")

    # 3. 计算核心指标
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print("\n" + "=" * 60)
    print("📊 评估报告")
    print("=" * 60)
    print(f"样本总数：{total}")
    print(f"准确率 (Accuracy)：{accuracy:.2%}")
    print(f"精确率 (Precision)：{precision:.2%}  -> 预测相关的里面，有多少是真的相关？")
    print(f"召回率 (Recall)：{recall:.2%}  -> 所有相关的里面，找出了多少？")
    print(f"F1 Score：{f1:.2%}")
    print(f"误报数 (FP)：{fp} | 漏报数 (FN)：{fn}")

    if errors:
        print("\n⚠️ Bad Case 分析 (共{}个)：".format(len(errors)))
        for err in errors:
            print(f"   - ID {err['id']}: 预期{err['expected']}，实际{err['got']}。理由：{err['reason']}")
    else:
        print("\n✅ 完美通过！没有误判案例。")

if __name__ == "__main__":
    evaluate_prompt_performance()
