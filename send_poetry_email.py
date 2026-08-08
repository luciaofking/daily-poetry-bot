#!/usr/bin/env python3
"""
每日诗歌导读邮件 — 云端自动发送脚本
在 GitHub Actions 上定时运行，无需本地电脑开机

工作原理：
1. 读取 poetry_data.json 中的诗歌导读内容
2. 根据当天日期匹配对应的 issue
3. 通过 SMTP 发送 HTML 邮件到指定邮箱

内容准备方式：
- 用 WorkBuddy 生成诗歌导读内容（如之前已做的第1期）
- 将内容添加到 poetry_data.json 文件中
- 推送到 GitHub 仓库，云端自动按日期发送
"""

import json
import smtplib
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

# ============ 配置 ============
BJT = timezone(timedelta(hours=8))
now = datetime.now(BJT)
today_str = now.strftime("%Y-%m-%d")

# SMTP 配置（从 GitHub Secrets 读取）
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
RECEIVER_EMAILS = os.environ.get("RECEIVER_EMAILS", "")

# 数据文件路径
DATA_FILE = "poetry_data.json"


def load_data():
    """读取诗歌数据文件"""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到数据文件 {DATA_FILE}")
        return None
    except json.JSONDecodeError as e:
        print(f"错误：数据文件 JSON 格式不正确: {e}")
        return None


def find_today_issue(data):
    """
    查找今天的诗歌内容
    优先精确匹配日期，如果没有则查找最近的未发送内容
    """
    issues = data.get("issues", [])
    if not issues:
        print("错误：数据文件中没有 issue")
        return None

    # 1. 尝试精确匹配今天的日期
    for issue in issues:
        if issue.get("date") == today_str:
            print(f"找到今日内容: {issue.get('subject', '无标题')}")
            return issue

    # 2. 如果没有精确匹配，找第一个日期 <= 今天的未发送内容
    for issue in issues:
        issue_date = issue.get("date", "")
        if issue_date and issue_date <= today_str:
            print(f"使用最近内容: {issue.get('subject', '无标题')} (日期: {issue_date})")
            return issue

    # 3. 如果都没有，说明还没有到任何内容的发布日期
    print(f"今天 ({today_str}) 没有可发送的内容")
    future_dates = [i.get("date", "?") for i in issues if i.get("date", "") > today_str]
    if future_dates:
        print(f"最近的发布日期: {future_dates[0]}")
    return None


def send_email(subject, html_body):
    """发送 HTML 邮件"""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("错误：缺少 SENDER_EMAIL 或 SENDER_PASSWORD")
        print("请在 GitHub 仓库 Settings → Secrets 中配置")
        return False

    if not RECEIVER_EMAILS:
        print("错误：缺少 RECEIVER_EMAILS")
        return False

    receivers = [r.strip() for r in RECEIVER_EMAILS.split(",") if r.strip()]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(receivers)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        print(f"正在发送邮件...")
        print(f"  收件人: {receivers}")
        print(f"  主题: {subject}")

        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()

        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, receivers, msg.as_string())
        server.quit()

        print("邮件发送成功！")
        return True

    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False


def main():
    print("=" * 50)
    print("每日诗歌导读邮件 — 云端自动发送")
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (CST)")
    print("=" * 50)

    # 1. 读取数据
    data = load_data()
    if not data:
        sys.exit(1)

    print(f"数据文件中共有 {len(data.get('issues', []))} 期内容")

    # 2. 查找今天的内容
    issue = find_today_issue(data)
    if not issue:
        print("今天无需发送邮件，退出。")
        sys.exit(0)

    # 3. 发送邮件
    subject = issue.get("subject", "每日诗歌导读")
    html_body = issue.get("html_body", "")

    if not html_body:
        print("错误：该 issue 没有邮件内容 (html_body)")
        sys.exit(1)

    success = send_email(subject, html_body)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
