import smtplib
import time
from email.mime.text import MIMEText


def send_QQ_email_plain():
    sender = user = '1124317604@qq.com'  # 发送方的邮箱账号
    passwd = 'frjdwipqtygpgefi'  # 授权码

    receiver = '2366692214@qq.com'  # 接收方的邮箱账号，不一定是QQ邮箱

    # 纯文本内容
    msg = MIMEText(f'Python 邮件发送测试 {time.time()}', 'plain', 'utf-8')

    # From 的内容是有要求的，前面的abc为自己定义的 nickname，如果是ASCII格式，则可以直接写
    msg['From'] = f'ric <1124317604@qq.com>'
    msg['To'] = receiver
    msg['Subject'] = 'Python SMTP 邮件测试'  # 点开详情后的标题

    try:
        # 建立 SMTP 、SSL 的连接，连接发送方的邮箱服务器
        smtp = smtplib.SMTP_SSL('smtp.qq.com', 465)

        # 登录发送方的邮箱账号
        smtp.login(user, passwd)

        # 发送邮件 发送方，接收方，发送的内容
        smtp.sendmail(sender, receiver, msg.as_string())

        print('邮件发送成功')

        smtp.quit()
    except Exception as e:
        print(e)
        print('发送邮件失败')

send_QQ_email_plain()