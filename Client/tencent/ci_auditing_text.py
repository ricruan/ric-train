import os
import uuid

from dotenv import load_dotenv

from Client.tencent.base import client

load_dotenv()

def ci_auditing_text_submit():
    # 用户自定义业务字段
    user_info = {
        'TokenId': '123456',  # 一般用于表示账号信息，长度不超过128字节
        'Nickname': '测试',  # 一般用于表示昵称信息，长度不超过128字节
        'DeviceId': '腾讯云',  # 一般用于表示设备信息，长度不超过128字节
        'AppId': '12500000',  # 一般用于表示 App 的唯一标识，长度不超过128字节
        'Room': '1',  # 一般用于表示房间号信息，长度不超过128字节
        'IP': '127.0.0.1',  # 一般用于表示 IP 地址信息，长度不超过128字节
        'Type': '测试',  # 一般用于表示业务类型，长度不超过128字节
        'ReceiveTokenId': '789123',  # 一般用于表示接收消息的用户账号，长度不超过128字节
        'Gender': '男',  # 一般用于表示性别信息，长度不超过128字节
        'Level': '100',  # 一般用于表示等级信息，长度不超过128字节
        'Role': '测试人员',  # 一般用于表示角色信息，长度不超过128字节
    }
    response = client.ci_auditing_text_submit(
        Bucket=os.getenv("TC_BUCKET_NAME"),  # 桶名称
        Content='123456test操你妈'.encode("utf-8"),  # 需要审核的文本内容
        BizType='',  # 表示审核策略的唯一标识
        # UserInfo=user_info,  # 用户自定义业务字段
        # DataId='456456456',  # 待审核的数据进行唯一业务标识
    )
    print(response)

ci_auditing_text_submit()