# Generated by Django 5.1.6 on 2025-02-28 10:53

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("agents", "0001_initial"),
        ("groups", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Message",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "message_type",
                    models.CharField(
                        choices=[
                            ("chat", "聊天消息"),
                            ("system", "系统消息"),
                            ("agent_response", "代理响应"),
                            ("join", "加入消息"),
                            ("leave", "离开消息"),
                            ("image", "图片消息"),
                            ("file", "文件消息"),
                            ("voice", "语音消息"),
                            ("rich_text", "富文本消息"),
                            ("markdown", "Markdown消息"),
                            ("task", "任务消息"),
                            ("task_update", "任务更新"),
                            ("poll", "投票消息"),
                            ("decision", "决策消息"),
                            ("handoff", "交接消息"),
                            ("error", "错误消息"),
                            ("status", "状态更新"),
                            ("settings", "设置变更"),
                        ],
                        max_length=20,
                        verbose_name="消息类型",
                    ),
                ),
                ("content", models.JSONField(verbose_name="消息内容")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "sender_type",
                    models.CharField(
                        choices=[("user", "用户"), ("agent", "代理"), ("system", "系统")],
                        max_length=10,
                        verbose_name="发送者类型",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(blank=True, default=dict, verbose_name="元数据"),
                ),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ws_messages",
                        to="groups.group",
                        verbose_name="接收群组",
                    ),
                ),
                (
                    "mentioned_agents",
                    models.ManyToManyField(
                        blank=True,
                        related_name="mentioned_in_ws_messages",
                        to="agents.agent",
                        verbose_name="提及代理",
                    ),
                ),
                (
                    "mentioned_users",
                    models.ManyToManyField(
                        blank=True,
                        related_name="mentioned_in_ws_messages",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="提及用户",
                    ),
                ),
                (
                    "parent_message",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="replies",
                        to="messaging.message",
                        verbose_name="父消息",
                    ),
                ),
                (
                    "recipient_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="received_ws_messages",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="接收用户",
                    ),
                ),
                (
                    "sender_agent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sent_ws_messages",
                        to="agents.agent",
                        verbose_name="发送代理",
                    ),
                ),
                (
                    "sender_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sent_ws_messages",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="发送用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "消息",
                "verbose_name_plural": "消息",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="MessageDeliveryStatus",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "is_delivered",
                    models.BooleanField(default=False, verbose_name="是否送达"),
                ),
                (
                    "delivered_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="送达时间"),
                ),
                ("is_read", models.BooleanField(default=False, verbose_name="是否已读")),
                (
                    "read_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="阅读时间"),
                ),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="delivery_statuses",
                        to="messaging.message",
                        verbose_name="消息",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="message_statuses",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "消息传递状态",
                "verbose_name_plural": "消息传递状态",
            },
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["created_at"], name="messaging_m_created_d51bc4_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["group"], name="messaging_m_group_i_539166_idx"),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["sender_user"], name="messaging_m_sender__aaaeb5_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["sender_agent"], name="messaging_m_sender__b95120_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["recipient_user"], name="messaging_m_recipie_6c8a9a_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="messagedeliverystatus",
            index=models.Index(
                fields=["message", "user"], name="messaging_m_message_b292e1_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="messagedeliverystatus",
            index=models.Index(
                fields=["user", "is_read"], name="messaging_m_user_id_05e51f_idx"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="messagedeliverystatus",
            unique_together={("message", "user")},
        ),
    ]
