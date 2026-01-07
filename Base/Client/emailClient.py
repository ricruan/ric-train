import logging
import mimetypes
import smtplib
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os

import dotenv

dotenv.load_dotenv()

# 获取项目根目录的绝对路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

def _to_absolute_path(file_path):
    """
    将相对路径转换为基于项目根目录的绝对路径
    """
    if os.path.isabs(file_path):
        return file_path
    return os.path.join(PROJECT_ROOT, file_path)

def send_email(
    sender_email,
    receiver_emails,
    subject,
    body,
    sender_password = os.getenv('EMAIL_PASSWORD'),
    smtp_server: str = 'smtp.qq.com',
    smtp_port: int = 465,
    is_html=False,
    attachments=None,  # 附件列表，每个元素是附件的路径
    inline_images=None
):
    """
    使用SMTP发送邮件的封装函数。

    Args:
        sender_email (str): 发件人邮箱地址。
        receiver_emails (list): 收件人邮箱地址列表。
        subject (str): 邮件主题。
        body (str): 邮件正文。
        sender_password (str): 发件人邮箱授权码或密码。
        smtp_server (str): SMTP服务器地址（例如：'smtp.qq.com'）。
        smtp_port (int): SMTP服务器端口（例如：465 或 587）。
        is_html (bool, optional): 邮件正文是否为HTML格式。默认为False (纯文本)。
        attachments (list, optional): 附件文件路径列表。默认为None。
        inline_images:
    Returns:
        bool: 邮件发送成功返回True，否则返回False。
    """
    try:
        # 创建一个MIMEMultipart对象，用于组合邮件内容和附件
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ', '.join(receiver_emails)
        msg['Subject'] = subject

        # 添加邮件正文
        if is_html:
            msg.attach(MIMEText(body, 'html', 'utf-8'))
        else:
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 添加内联图片
        if inline_images:
            for img_path, content_id in inline_images:
                # 转换为绝对路径
                abs_img_path = _to_absolute_path(img_path)
                if not os.path.exists(abs_img_path):
                    logger.warning(f"警告：内联图片文件不存在 - {abs_img_path} (原始路径: {img_path})")
                    continue
                # 猜测图片MIME类型
                ctype, encoding = mimetypes.guess_type(img_path)
                if ctype is None or encoding is not None:
                    ctype = 'application/octet-stream'  # 无法猜测时使用通用类型
                maintype, subtype = ctype.split('/', 1)
                with open(abs_img_path, 'rb') as fp:
                    if maintype == 'image':
                        img = MIMEImage(fp.read(), _subtype=subtype)
                    else:  # 如果不是图片类型，作为普通应用附件处理
                        img = MIMEApplication(fp.read(), _subtype=subtype)
                    img.add_header('Content-ID', f'<{content_id}>')  # 设置Content-ID
                    img.add_header('Content-Disposition', 'inline', filename=os.path.basename(abs_img_path))
                    msg.attach(img)

        # 添加附件
        if attachments:
            if isinstance(attachments,str):
                attachments = [attachments]
            for attachment_path in attachments:
                # 转换为绝对路径
                abs_attachment_path = _to_absolute_path(attachment_path)
                if not os.path.exists(abs_attachment_path):
                    logger.warning(f"警告：附件文件不存在 - {abs_attachment_path} (原始路径: {attachment_path})")
                    continue

                with open(abs_attachment_path, 'rb') as f:
                    part = MIMEApplication(f.read(), _subtype=os.path.basename(abs_attachment_path).split('.')[-1])
                    part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(abs_attachment_path))
                    msg.attach(part)

        # 连接SMTP服务器
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)  # SSL加密
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()  # TLS加密 (如果端口不是465，通常需要启动TLS)

        # 登录邮箱
        server.login(sender_email, sender_password)

        # 发送邮件
        server.sendmail(sender_email, receiver_emails, msg.as_string())

        # 关闭连接
        server.quit()
        logger.info("邮件发送成功！")
        return True

    except Exception as e:
        logger.error(f"邮件发送失败：{e}")
        return False

if __name__ == '__main__':
    # --- 邮件配置示例 ---
    SMTP_SERVER = 'smtp.qq.com'  # 例如：QQ邮箱SMTP服务器
    SMTP_PORT = 465             # QQ邮箱SSL端口
    SENDER_EMAIL = '1124317604@qq.com'  # 你的邮箱
    SENDER_PASSWORD = 'frjdwipqtygpgefi'  # 你的邮箱授权码，不是登录密码

    RECEIVER_EMAILS = ['2366692214@qq.com', '1053851332@qq.com'] # 收件人列表
    EMAIL_SUBJECT = '测试邮件'
    EMAIL_BODY_TEXT = '这是一封测试邮件，由Python脚本发送。'
    EMAIL_BODY_HTML = """
    <html>
    <body>
        <p><img src="cid:my_logo" alt="Python Logo"></p>
        <h1>你好！</h1>
        <p>这是一封<b>HTML</b>格式的测试邮件，由Python脚本发送。</p>
        <p>祝你今天愉快！</p>
    </body>
    </html>
    """

    # --- 创建一个虚拟附件文件用于测试 ---
    with open('test_attachment.txt', 'w', encoding='utf-8') as f:
        f.write("这是一个测试附件的内容。")
    ATTACHMENTS = ['test_attachment.txt']

    print("--- 发送纯文本邮件 ---")
    success_text = send_email(
        sender_email=SENDER_EMAIL,
        receiver_emails=RECEIVER_EMAILS,
        subject=EMAIL_SUBJECT + " (纯文本)",
        body=EMAIL_BODY_TEXT,
        inline_images=[('test.png', 'my_logo')]
    )
    print(f"纯文本邮件发送结果: {success_text}\n")

    print("--- 发送HTML邮件带附件 ---")
    success_html_attachment = send_email(
        sender_email=SENDER_EMAIL,
        receiver_emails=RECEIVER_EMAILS,
        subject=EMAIL_SUBJECT + " (HTML带附件)",
        body=EMAIL_BODY_HTML,
        is_html=True,
        attachments=ATTACHMENTS,
        inline_images=[('test.png', 'my_logo')]
    )
    print(f"HTML带附件邮件发送结果: {success_html_attachment}\n")

    # --- 清理测试附件 ---
    if os.path.exists('test_attachment.txt'):
        os.remove('test_attachment.txt')
        print("已清理测试附件: test_attachment.txt")