"""
命令行测试后端生成流程：输入文字，直接获得生成结果。
"""
import asyncio
from app.services.orchestrator import orchestrator


# 直接在这里设置你的测试输入
query = "【教师活动】：教师用英语向学生问好，并带领学生进行简单的问候练习。\n- 教师：“Good morning, class!”\n- 学生（齐声回答）：“Good morning, teacher!”\n - 教师：“How are you today?”\n- 学生（齐声回答）：“I’m fine, thank you. And you?”\n- 教师：“I’m fine, too. Thank you!”\n\n【学生活动】：学生跟随教师进行问候练习，熟悉课堂氛围。\n\n【活动意图】：通过问候热身，营造轻松愉快的课堂氛围，帮助学生进入英语学习状态。\n\n【效果评价】：学生能够积极参与问候练习，语音语调自然流畅。\n【活动意图】：通过问候热身，营造轻松愉快的课堂氛围，帮助学生进入英语学习状态。\n【效果评价】：学生能够积极参与问候练习，语音语调自然流畅。"

async def main():
    print(f"测试输入: {query}\n")
    print("--- 生成流程开始 ---\n")
    async for event in orchestrator.generate_stream(query):
        # 只打印主要阶段和最终结果
        if event.get("event") == "complete":
            print(f"\n[完成] 结果ID: {event['result_id']}")
            print(f"HTML文件: outputs/{event['result_id']}.html")
        elif event.get("event") == "error":
            print(f"[错误] {event.get('message')}")
        elif event.get("event") in {"analysis_start", "analysis_done", "dsl_start", "dsl_done", "runtime_start", "postprocess_start"}:
            print(f"[{event['event']}] {event.get('message', '')}")

if __name__ == "__main__":
    asyncio.run(main())
