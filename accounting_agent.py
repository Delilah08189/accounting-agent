from openai import OpenAI
import json
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LEDGER_FILE = "ledger.csv"

# 初始化账本
def init_ledger():
    if not os.path.exists(LEDGER_FILE):
        df = pd.DataFrame(columns=[
            "date", "type", "amount", "debit", "credit", "desc"
        ])
        df.to_csv(LEDGER_FILE, index=False)

# 添加会计分录
def add_entry(entry_type: str, amount: float, desc: str):
    df = pd.read_csv(LEDGER_FILE)
    date = datetime.now().strftime("%Y-%m-%d")

    if entry_type == "income":
        debit = "银行存款"
        credit = "主营业务收入"
    elif entry_type == "expense":
        debit = "管理费用"
        credit = "银行存款"
    else:
        debit = credit = "未知"

    new_row = {
        "date": date,
        "type": entry_type,
        "amount": amount,
        "debit": debit,
        "credit": credit,
        "desc": desc
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(LEDGER_FILE, index=False)
    return f"已记账：{entry_type} {amount:.2f}元｜摘要：{desc}"

# 查看财务概况
def get_balance():
    if not os.path.exists(LEDGER_FILE):
        return "暂无记账数据"
    df = pd.read_csv(LEDGER_FILE)
    if df.empty:
        return "暂无记账数据"

    total_income = df[df["type"] == "income"]["amount"].sum()
    total_expense = df[df["type"] == "expense"]["amount"].sum()
    profit = total_income - total_expense

    return f"""
📊 简易财务报表
总收入：{total_income:.2f} 元
总支出：{total_expense:.2f} 元
利润：{profit:.2f} 元
"""

# 计算企业所得税
def calculate_tax(profit: float, tax_rate: float = 0.25):
    tax = profit * tax_rate
    net_profit = profit - tax
    return f"""
🧾 企业所得税计算
税前利润：{profit:.2f} 元
税率：{tax_rate:.1%}
所得税：{tax:.2f} 元
净利润：{net_profit:.2f} 元
"""

# 工具列表
tools = [
    {
        "type": "function",
        "function": {
            "name": "add_entry",
            "description": "添加会计分录，收入或支出",
            "parameters": {
                "type": "object",
                "properties": {
                    "entry_type": {"type": "string", "enum": ["income", "expense"]},
                    "amount": {"type": "number"},
                    "desc": {"type": "string"}
                },
                "required": ["entry_type", "amount", "desc"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_balance",
            "description": "查询总收入、总支出、利润"
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_tax",
            "description": "根据税前利润计算企业所得税",
            "parameters": {
                "type": "object",
                "properties": {
                    "profit": {"type": "number"},
                    "tax_rate": {"type": "number", "default": 0.25}
                },
                "required": ["profit"]
            }
        }
    }
]

# 执行工具
def execute_tool(name, args):
    if name == "add_entry":
        return add_entry(args["entry_type"], args["amount"], args["desc"])
    elif name == "get_balance":
        return get_balance()
    elif name == "calculate_tax":
        return calculate_tax(args["profit"], args.get("tax_rate", 0.25))
    return "未知工具"

# Agent对话主逻辑
def agent_chat(user_input):
    init_ledger()
    messages = [
        {"role": "system", "content": "你是专业会计助手，规范记账、算税、生成报表，回答简洁专业"},
        {"role": "user", "content": user_input}
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    msg = response.choices[0].message
    if not msg.tool_calls:
        return msg.content

    for tc in msg.tool_calls:
        func_name = tc.function.name
        func_args = json.loads(tc.function.arguments)
        result = execute_tool(func_name, func_args)
        messages.append(msg)
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result
        })

    final = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    return final.choices[0].message.content

# 运行
if __name__ == "__main__":
    print("💼 会计Agent已启动（输入 exit 退出）")
    while True:
        user = input("你：")
        if user.lower() in ["exit", "quit", "q"]:
            break
        ans = agent_chat(user)
        print("Agent：", ans, "\n")
