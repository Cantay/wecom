# -*- coding: utf-8 -*-

import logging
import time
import io
import requests
import json
import base64
import logging
from datetime import datetime, timedelta
from PIL import Image
from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, Warning
from odoo.modules.module import get_module_resource
from odoo.addons.wecom_api.api.wecom_abstract_api import ApiException


_logger = logging.getLogger(__name__)


class WeComChatData(models.Model):
    _name = "wecom.chatdata"
    _description = "Wecom Chat Data"
    _order = "seq desc"

    name = fields.Char(string="Name", compute="_compute_name")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    commented = fields.Boolean(string="Commented")
    seq = fields.Integer(
        string="Message sequence number",
        help="When pulling again, you need to bring the largest SEQ in the last packet.",
    )
    msgid = fields.Char(
        string="Message ID", help="You can use this field for message de duplication."
    )
    is_external_msg = fields.Boolean(
        string="External message", compute="_compute_is_external_msg"
    )

    publickey_ver = fields.Integer(
        string="Public key version",
        help="The version number of the public key used to encrypt this message.",
    )
    encrypt_random_key = fields.Char(string="Encrypt random key")
    encrypt_chat_msg = fields.Char(string="Encrypt chat message")
    decrypted_chat_msg = fields.Text(string="Decrypted chat message")

    action = fields.Selection(
        string="Message Action",
        selection=[
            ("send", "Send message"),
            ("recall", "Recall message"),
            ("switch", "Switch enterprise log"),
        ],
    )
    from_user = fields.Char(
        string="Message sender ID", help="The user who sent the message."
    )
    tolist = fields.Char(string="Message recipient list")

    roomid = fields.Char(string="Group chat ID")
    room_name = fields.Char(string="Group chat name")
    room_creator = fields.Char(string="Group chat creator")
    room_create_time = fields.Datetime(string="Group chat create time")
    room_notice = fields.Text(string="Group chat notice")
    room_members = fields.Text(string="Group chat members")

    msgtime = fields.Datetime(string="Message time")
    msgtype = fields.Selection(
        string="Message type",
        selection=[
            ("text", "Text message"),
            ("image", "Image message"),
            ("revoke", "Revoke message"),
            ("agree", "Agree message"),
            ("disagree", "Disagree message"),
            ("voice", "Voice message"),
            ("video", "Video message"),
            ("card", "Card message"),
            ("location", "Location message"),
            ("emotion", "Emotion message"),
            ("file", "File message"),
            ("link", "Link message"),
            ("weapp", "Weapp message"),
            ("chatrecord", "Chat record message"),
            ("todo", "Todo message"),
            ("vote", "Vote message"),
            ("collect", "Collect message"),
            ("redpacket", "Red packet message"),
            ("meeting", "Meeting invitation message"),
            ("docmsg", "Online document messages"),
            ("markdown", "MarkDown messages"),
            ("news", "News messages"),
            ("calendar", "Calendar messages"),
            ("mixed", "Mixed messages"),
            ("meeting_voice_call", "Audio archive message"),
            ("voip_doc_share", "Audio shared document messages"),
            ("external_redpacket", "Interworking red packet messages"),
            ("sphfeed", "Video account messages"),
        ],
    )
    time = fields.Datetime(string="Message sending time",)
    user = fields.Char(string="User")

    text = fields.Text(string="Text message content")  # msgtype=text
    image = fields.Text(string="Image message content")  # msgtype=image
    revoke = fields.Text(string="Revoke message content")  # msgtype=revoke
    agree = fields.Text(string="Agree message content")  # msgtype=agree
    disagree = fields.Text(string="Disagree message content")  # msgtype=disagree
    voice = fields.Text(string="Voice message content")  # msgtype=voice
    video = fields.Text(string="Video message content")  # msgtype=video
    card = fields.Text(string="Card message content")  # msgtype=card
    location = fields.Text(string="Location message content")  # msgtype=location
    emotion = fields.Text(string="Emotion message content")  # msgtype=emotion
    file = fields.Text(string="File message content")  # msgtype=file
    link = fields.Text(string="Link message content")  # msgtype=link
    weapp = fields.Text(string="Weapp message content")  # msgtype=weapp
    chatrecord = fields.Text(string="Chat record message content")  # msgtype=chatrecord
    todo = fields.Text(string="Todo message content")  # msgtype=todo
    vote = fields.Text(string="Vote message content")  # msgtype=vote
    collect = fields.Text(string="Collect message content")  # msgtype=collect
    redpacket = fields.Text(string="Red packet message content")  # msgtype=redpacket
    meeting = fields.Text(
        string="Meeting invitation message content"
    )  # msgtype=meeting
    docmsg = fields.Text(string="Online document messages content")  # msgtype=docmsg
    markdown = fields.Text(string="MarkDown messages content")  # msgtype=markdown
    news = fields.Text(string="News messages content")  # msgtype=news
    calendar = fields.Text(string="Calendar messages content")  # msgtype=calendar
    mixed = fields.Text(string="Mixed messages content")  # msgtype=mixed
    meeting_voice_call = fields.Text(
        string="Audio archive message content"
    )  # msgtype=meeting_voice_call
    voip_doc_share = fields.Text(
        string="Audio shared document messages content"
    )  # msgtype=voip_doc_share
    external_redpacket = fields.Text(
        string="Interworking red packet messages content"
    )  # msgtype=external_redpacket
    sphfeed = fields.Text(string="Video account messages content")  # msgtype=sphfeed

    @api.depends("msgid", "action")
    def _compute_name(self):
        for record in self:
            if record.room_name:
                record.name = record.room_name
            else:
                record.name = record.msgid

    @api.depends("msgid", "action")
    def _compute_is_external_msg(self):
        for record in self:
            if "external" in record.msgid:
                record.is_external_msg = True
            else:
                record.is_external_msg = False

    def download_chatdatas(self):
        """
        获取聊天记录
        注:获取会话记录内容不能超过3天，如果企业需要全量数据，则企业需要定期拉取聊天消息。返回的ChatDatas内容为json格式。
        """
        company = self.company_id
        if not company:
            company = self.env.company

        corpid = company.corpid
        if corpid == False:
            raise UserError(_("Corp ID cannot be empty!"))
        if company.msgaudit_app_id is False:
            raise UserError(
                _(
                    "Please bind the session content archiving application on the settings page."
                )
            )
        secret = company.msgaudit_app_id.secret
        if secret == False:
            raise UserError(
                _(
                    "The application secret key of session content archive cannot be empty!"
                )
            )

        private_keys = company.msgaudit_app_id.private_keys
        if len(private_keys) == 0:
            raise UserError(_("No message encryption key exists!"))
        key_list = []

        for key in private_keys:
            key_dic = {
                "publickey_ver": key.publickey_ver,
                "private_key": key.private_key,
            }
            key_list.append(key_dic)

        # 首次访问填写0，非首次使用上次企业微信返回的最大seq。允许从任意seq重入拉取。
        max_seq_id = 0
        self.env.cr.execute(
            """
            SELECT MAX(seq)
            FROM wecom_chatdata
            WHERE company_id=%s
            """
            % (company.id)
        )
        results = self.env.cr.dictfetchall()
        if results[0]["max"] is not None:
            max_seq_id = results[0]["max"]

        try:
            ir_config = self.env["ir.config_parameter"].sudo()
            msgaudit_sdk_url = ir_config.get_param("wecom.msgaudit.msgaudit_sdk_url")
            msgaudit_chatdata_url = ir_config.get_param(
                "wecom.msgaudit.msgaudit_chatdata_url"
            )

            chatdata_url = msgaudit_sdk_url + msgaudit_chatdata_url

            proxy = (
                True
                if ir_config.get_param("wecom.msgaudit_sdk_proxy") == "True"
                else False
            )
            headers = {"content-type": "application/json"}
            body = {
                "seq": max_seq_id,
                "corpid": corpid,
                "secret": secret,
                "private_keys": key_list,
            }

            if proxy:
                body.update(
                    {"proxy": msgaudit_chatdata_url, "paswd": "odoo:odoo",}
                )

            r = requests.get(chatdata_url, data=json.dumps(body), headers=headers)
            chat_datas = r.json()

            if len(chat_datas) > 0:
                for data in chat_datas:
                    dic_data = {}
                    dic_data = {
                        "seq": data["seq"],
                        "msgid": data["msgid"],
                        "publickey_ver": data["publickey_ver"],
                        "encrypt_random_key": data["encrypt_random_key"],
                        "encrypt_chat_msg": data["encrypt_chat_msg"],
                        "decrypted_chat_msg": json.dumps(data["decrypted_chat_msg"]),
                    }

                    # 以下为解密聊天信息内容
                    for key, value in data["decrypted_chat_msg"].items():
                        if key == "msgid" or key == "voiceid":
                            pass
                        elif key == "from":
                            dic_data["from_user"] = value
                        elif key == "msgtime" or key == "time":
                            time_stamp = value
                            dic_data[key] = self.timestamp2datetime(time_stamp)
                        else:
                            dic_data[key] = value

                    self.sudo().create(dic_data)
                return True
            else:
                return False
        except ApiException as e:
            return self.env["wecomapi.tools.action"].ApiExceptionDialog(
                e, raise_exception=True
            )
        except Exception as e:
            _logger.exception("Exception: %s" % e)
            return str(e)

    @api.model
    def _default_image(self):
        image_path = get_module_resource(
            "wecom_api", "static/src/img", "default_image.png"
        )
        return base64.b64encode(open(image_path, "rb").read())

    def update_group_chat(self):
        """
        更新群聊信息
        """
        company = self.company_id
        if not company:
            company = self.env.company

        try:
            wxapi = self.env["wecom.service_api"].InitServiceApi(
                company.corpid, company.msgaudit_app_id.secret
            )
            response = wxapi.httpCall(
                self.env["wecom.service_api_list"].get_server_api_call("GROUPCHAT_GET"),
                {"roomid": self.roomid},
            )
            if response["errcode"] == 0:
                time_stamp = response["room_create_time"]
                room_create_time = self.timestamp2datetime(time_stamp)
                self.write(
                    {
                        "room_name": response["roomname"],
                        "room_creator": response["creator"],
                        "room_notice": response["notice"],
                        "room_create_time": room_create_time,
                        "room_members": json.dumps(response["members"]),
                    }
                )
                same_group_chats = self.search([("roomid", "=", self.roomid)])
                for chat in same_group_chats:
                    chat.write(
                        {"room_name": response["roomname"],}
                    )
        except ApiException as ex:
            return self.env["wecomapi.tools.action"].ApiExceptionDialog(
                ex, raise_exception=True
            )

    def get_decrypted_chat_msg_fields(self):
        fields = [f for f in self._fields.keys()]
        remove_field = [
            "id",
            "name",
            "company_id",
            "seq",
            "msgid",
            "publickey_ver",
            "encrypt_random_key",
            "encrypt_chat_msg",
            "decrypted_chat_msg",
            "create_date",
            "create_uid",
            "write_date",
            "write_uid",
            "__last_update",
        ]
        for r in remove_field:
            fields.remove(r)
        return fields

    def timestamp2datetime(self, time_stamp):
        """
        时间戳转日期时间
        """
        if len(str(time_stamp)) > 10:
            # 一般爬取下来的时间戳长度都是13位的数字，而time.localtime的参数要的长度是10位，所以我们需要将其/1000并取整即可
            time_stamp = int(time_stamp / 1000)
        loc_time = time.localtime(time_stamp)
        return time.strftime("%Y-%m-%d %H:%M:%S", loc_time)

    def cron_download_chatdatas(self):
        """
        自动任务定时下载聊天记录
        """
        for app in self.env["wecom.apps"].search(
            [("company_id", "!=", False), ("type_code", "=", "['msgaudit']")]
        ):
            _logger.info(
                _("Automatic task: Start download session content record for [%s]")
                % app.company_id.name
            )
            corpid = app.company_id.corpid
            secret = app.secret
            private_keys = app.private_keys
            key_list = []

            for key in private_keys:
                key_dic = {
                    "publickey_ver": key.publickey_ver,
                    "private_key": key.private_key,
                }
                key_list.append(key_dic)
            # 首次访问填写0，非首次使用上次企业微信返回的最大seq。允许从任意seq重入拉取。
            max_seq_id = 0
            self.env.cr.execute(
                """
                SELECT MAX(seq)
                FROM wecom_chatdata
                WHERE company_id=%s
                """
                % (app.company_id.id)
            )
            results = self.env.cr.dictfetchall()
            if results[0]["max"] is not None:
                max_seq_id = results[0]["max"]

            try:
                ir_config = self.env["ir.config_parameter"].sudo()
                msgaudit_sdk_url = ir_config.get_param(
                    "wecom.msgaudit.msgaudit_sdk_url"
                )
                msgaudit_chatdata_url = ir_config.get_param(
                    "wecom.msgaudit.msgaudit_chatdata_url"
                )

                chatdata_url = msgaudit_sdk_url + msgaudit_chatdata_url

                proxy = (
                    True
                    if ir_config.get_param("wecom.msgaudit_sdk_proxy") == "True"
                    else False
                )
                headers = {"content-type": "application/json"}
                body = {
                    "seq": max_seq_id,
                    "corpid": corpid,
                    "secret": secret,
                    "private_keys": key_list,
                }
                if proxy:
                    body.update(
                        {"proxy": msgaudit_chatdata_url, "paswd": "odoo:odoo",}
                    )

                r = requests.get(chatdata_url, data=json.dumps(body), headers=headers)
                chat_datas = r.json()

                if len(chat_datas) > 0:
                    for data in chat_datas:
                        dic_data = {}
                        dic_data = {
                            "company_id": app.company_id.id,
                            "seq": data["seq"],
                            "msgid": data["msgid"],
                            "publickey_ver": data["publickey_ver"],
                            "encrypt_random_key": data["encrypt_random_key"],
                            "encrypt_chat_msg": data["encrypt_chat_msg"],
                            "decrypted_chat_msg": json.dumps(
                                data["decrypted_chat_msg"]
                            ),
                        }

                        # 以下为解密聊天信息内容
                        for key, value in data["decrypted_chat_msg"].items():
                            if key == "msgid":
                                pass
                            elif key == "from":
                                dic_data["from_user"] = value
                            elif key == "msgtime" or key == "time":
                                time_stamp = value
                                dic_data[key] = self.timestamp2datetime(time_stamp)
                            else:
                                dic_data[key] = value

                        self.sudo().create(dic_data)
                    _logger.info(
                        _(
                            "Automatic task: End download session content record for [%s]"
                        )
                        % app.company_id.name
                    )
                else:
                    _logger.info(
                        _(
                            "Automatic task: End download session content record for [%s],There are no records to download."
                        )
                        % app.company_id.name
                    )
            except ApiException as e:
                _logger.exception(
                    _(
                        "Automatic task: Exception in downloading session content record for [%s],Exception:%s"
                    )
                    % (app.company_id.name, str(e))
                )
            except Exception as e:
                _logger.exception(
                    _(
                        "Automatic task: Exception in downloading session content record for [%s],Exception:%s"
                    )
                    % (app.company_id.name, str(e))
                )

    # ------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------
    def format_content(self):
        """
        格式化内容
        """
        if self.commented:
            return

        company = self.company_id
        if not company:
            company = self.env.company

        corpid = company.corpid

        if company.msgaudit_app_id is False:
            raise UserError(
                _(
                    "Please bind the session content archiving application on the settings page."
                )
            )
        secret = company.msgaudit_app_id.secret
        private_keys = company.msgaudit_app_id.private_keys
        key_list = []

        for key in private_keys:
            key_dic = {
                "publickey_ver": key.publickey_ver,
                "private_key": key.private_key,
            }
            key_list.append(key_dic)

        content = self[self._fields[self.msgtype].name]

        if content[0] == "{":
            # 如果是json格式的内容
            msg_send_time = self.msgtime
            msg_send_seq = self.seq
            msg_sender_name = _("External personnel:") + self.from_user

            msg_sender = self.env["hr.employee"].search(
                [("wecom_userid", "=", self.from_user)], limit=1
            )
            if msg_sender:
                msg_sender_name = _("Internal staff:") + msg_sender.name

            msg_content = self[self._fields[self.msgtype].name]

            if self.msgtype == "text":
                # 文本消息
                if "content" in msg_content:
                    content = eval(msg_content)["content"]
            elif self.msgtype == "link":
                # 链接消息
                link = eval(msg_content)
                content = """
                <div class="card mt-3">
                    <div class="row no-gutters">
                        <div class="col-md-4">
                            <img src="%s" alt="%s">
                        </div>
                        <div class="col-md-8">
                            <div class="card-body">
                                <h5 class="card-title">%s</h5>
                                <p class="card-text">%s</p>
                                <p class="card-text"><small class="text-muted">
                                    <a href="%s" target="_blank">%s</a>
                                </small></p>
                            </div>
                        </div>
                    </div>
                </div>
                """ % (
                    link["image_url"],
                    link["title"],
                    link["title"],
                    link["description"],
                    link["link_url"],
                    _("Open link"),
                )
            elif self.msgtype == "image":
                # 图片消息
                try:
                    ir_config = self.env["ir.config_parameter"].sudo()
                    mediadata_url = ir_config.get_param(
                        "wecom.msgaudit.msgaudit_sdk_url"
                    ) + ir_config.get_param("wecom.msgaudit.msgaudit_mediadata_url")
                    proxy = (
                        True
                        if ir_config.get_param("wecom.msgaudit_sdk_proxy") == "True"
                        else False
                    )

                    headers = {"content-type": "application/json"}
                    body = {
                        "seq": 0,
                        "sdkfileid": eval(msg_content)["sdkfileid"],
                        "corpid": corpid,
                        "secret": secret,
                        "private_keys": key_list,
                    }
                    if proxy:
                        body.update(
                            {"proxy": mediadata_url, "paswd": "odoo:odoo",}
                        )
                    r = requests.get(
                        mediadata_url, data=json.dumps(body), headers=headers
                    )
                    mediadata = r.json()

                    img_max_size = (
                        int(
                            ir_config.get_param(
                                "wecom.msgaudit.chatdata2contacts.img_max_size"
                            )
                        )
                        * 1024
                    )  # 图片最大大小，超过此大小，进行压缩
                    filesize = eval(msg_content)["filesize"]  # 图片原始大小
                    # base64_source_str = base64.b64encode(mediadata).decode()
                    base64_source_str = self.compress_image_base64(
                        # base64.b64encode(mediadata), img_max_size, filesize
                        bytes(mediadata, "utf-8"),
                        img_max_size,
                        filesize,
                    )
                    # print("data:image/png;base64,%s" % base64_source_str.decode())
                    content = (
                        "<p><img class='mw-100' src='data:image/png;base64,%s' /></p>"
                        % base64_source_str.decode()
                    )
                except Exception as e:
                    _logger.exception("Exception: %s" % e)
                    if "HTTPConnectionPool" in str(e):
                        raise UserError(_("API interface not started!"))

            else:
                pass

            media_content = """<div class="media wecom_chat_record">
                <div class="media-body">
                    <h5 class="mt-0"><span class='contacts' title='%s'>%s</span> <small>%s %s</small> <small>%s %s</small></h5>
                    %s
                </div>
            </div>
            """ % (
                msg_sender_name,
                msg_sender_name,
                _("Sending time:"),
                msg_send_time,
                _("Message sequence number:"),
                msg_send_seq,
                content,
            )
            # print(media_content)
            self.write({self._fields[self.msgtype].name: media_content})

    def compress_image_base64(self, base64_source, t_size, o_size):
        """
        不改变图片尺寸压缩到指定大小
        :param base64_source: 图像base64编码
        :param t_size: 目标大小
        :param o_size: 原大小
        :return: 返回压缩后的base64编码
        """
        if o_size <= t_size:
            return base64_source
        else:
            with io.BytesIO(base64.b64decode(base64_source)) as im:
                o_size = len(im.getvalue())  # 原始图片大小
                stream = im
                while o_size > t_size:
                    imgage = Image.open(stream)
                    x, y = imgage.size
                    output = imgage.resize(
                        (int(x * 0.9), int(y * 0.9)), Image.ANTIALIAS
                    )
                    stream.close()
                    stream = io.BytesIO()
                    output.save(stream, "png")
                    o_size = len(stream.getvalue())  # 压缩后图片大小
                base64_source = base64.b64encode(stream.getvalue()).decode()
                stream.close()
                return base64_source
