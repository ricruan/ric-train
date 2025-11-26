import os

from dotenv import load_dotenv

from Client.emailClient import send_email


load_dotenv()

class EmailService:

    def __init__(self,receiver_emails: list[str] = None):
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.receiver_emails = receiver_emails or ['2366692214@qq.com', '1053851332@qq.com','2956090912@qq.com']




    def send_emails_ric(self,
                        subject:str,
                        email_content:str,
                        receiver_emails: list[str] = None,
                        is_html:bool=False,
                        attachments= None,
                        inline_images=None):
        """
        发送邮件
        :param subject: 邮件标题
        :param email_content: 邮件内容
        :param receiver_emails: 收件人邮箱
        :param is_html:  是否是HTML格式
        :param attachments: 附件
        :param inline_images: 图片
        :return:
        """
        send_email(sender_email=self.sender_email,
                   receiver_emails=receiver_emails or self.receiver_emails,
                   subject=subject,
                   body=email_content,
                   is_html=is_html,
                   attachments=attachments,
                   inline_images=inline_images)




if __name__ == '__main__':
    email_service = EmailService()
    email_service.send_emails_ric(subject='❤情书❤' ,email_content="测试邮件",attachments="../Wolin/output_docxtpl.docx")