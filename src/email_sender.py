"""
邮件发送模块
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import json
from datetime import datetime
import os


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, smtp_server: str, smtp_port: int, sender_email: str, sender_password: str):
        """
        初始化邮件发送器
        
        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            sender_email: 发送邮箱
            sender_password: 授权码
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
    
    def send_paper_report(self, to_email: str, task_name: str, keywords: str, papers: list,
                          unsubscribe_url: str = None, manage_url: str = None) -> bool:
        """发送论文报告邮件"""
        if not papers:
            return self._send_empty_report(to_email, task_name, keywords)

        subject = f"📚 论文推荐报告 - {task_name} - {datetime.now().strftime('%Y-%m-%d')}"
        html_content = self._generate_html_report(task_name, keywords, papers, unsubscribe_url, manage_url)
        return self._send_email(to_email, subject, html_content)
    
    def _generate_html_report(self, task_name: str, keywords: str, papers: list,
                              unsubscribe_url: str = None, manage_url: str = None) -> str:
        """生成HTML格式的论文报告"""
        
        papers_html = ""
        for i, paper in enumerate(papers, 1):
            papers_html += f"""
            <div style="margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #eee;">
                <h3 style="color: #2c3e50;">{i}. {paper.get('title_cn', paper.get('title', '无标题'))}</h3>
                <p><strong>英文标题：</strong> {paper.get('title', '无')}</p>
                <p><strong>期刊：</strong> {paper.get('journal_name', '未知')}</p>
                <p><strong>作者：</strong> {', '.join(paper.get('authors', ['未知'])[:3])}</p>
                <p><strong>发表日期：</strong> {paper.get('pub_date', '未知')}</p>
                <p><strong>DOI：</strong> <a href="{paper.get('url', '#')}" style="color: #3498db;" target="_blank">{paper.get('doi', '无')}</a></p>
                <p><strong>筛选理由：</strong> {paper.get('filter_reason', '无')}</p>
                <p><strong>中文摘要：</strong> {paper.get('summary_cn', '暂无')}</p>
            </div>
            """
        
        footer_links = ""
        if unsubscribe_url or manage_url:
            parts = []
            if unsubscribe_url:
                parts.append(f'<a href="{unsubscribe_url}" style="color:#e74c3c;">取消订阅</a>')
            if manage_url:
                parts.append(f'<a href="{manage_url}" style="color:#3498db;">管理订阅</a>')
            footer_links = '<p style="margin-top:8px;">' + ' | '.join(parts) + '</p>'

        html = f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #2c3e50, #3498db); color: white; padding: 20px; border-radius: 10px; text-align: center; }}
                .content {{ padding: 20px; }}
                .footer {{ text-align: center; padding: 20px; color: #7f8c8d; font-size: 12px; border-top: 1px solid #eee; }}
                .summary {{ background: #e8f4fd; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📚 论文推荐报告</h1>
                    <p>基于AI智能筛选</p>
                </div>
                <div class="content">
                    <h2>任务信息</h2>
                    <p><strong>任务名称：</strong> {task_name}</p>
                    <p><strong>关键词：</strong> {keywords}</p>
                    <p><strong>生成时间：</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>相关论文数：</strong> {len(papers)} 篇</p>

                    <div class="summary">
                        <h3>📊 搜索摘要</h3>
                        <p>本次搜索共找到 {len(papers)} 篇与"{keywords}"相关的论文。</p>
                    </div>

                    <h2>📄 论文列表</h2>
                    {papers_html}
                </div>
                <div class="footer">
                    <p>论文推荐系统 | 由 AI 自动生成</p>
                    {footer_links}
                </div>
            </div>
        </body>
        </html>"""
        
        return html
    
    def _send_empty_report(self, to_email: str, task_name: str, keywords: str) -> bool:
        """发送空报告（未找到相关论文）"""
        subject = f"📚 论文推荐报告 - {task_name} - 未找到相关论文"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif;">
            <h2>📚 论文推荐报告</h2>
            <p><strong>任务名称：</strong> {task_name}</p>
            <p><strong>关键词：</strong> {keywords}</p>
            <p><strong>生成时间：</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <div style="background: #fff3cd; padding: 15px; border-radius: 5px;">
                <p>⚠️ 未找到与 "{keywords}" 相关的论文</p>
                <p>建议：尝试更宽泛的关键词，或扩大时间范围。</p>
            </div>
            <hr>
            <p style="color: #7f8c8d; font-size: 12px;">论文推荐系统 | 由 AI 自动生成</p>
        </body>
        </html>
        """
        
        return self._send_email(to_email, subject, html)
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """发送邮件"""
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = self.sender_email
            msg['To'] = to_email
            
            # 添加HTML内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 连接SMTP服务器并发送
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            print(f"[OK] 邮件已发送至 {to_email}")
            return True
            
        except Exception as e:
            print(f"[ERR] 邮件发送失败: {e}")
            return False