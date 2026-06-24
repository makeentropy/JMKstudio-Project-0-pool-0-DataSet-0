from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import uuid
import threading
import time
from typing import Optional
from ..config import Config
from ..llm import LLMFactory
from ..email_service import EmailService
from ..agent import ChatAgent, EmailAgent


class HTTPServer:
    def __init__(self, config: Config):
        self.config = config
        self.app = Flask(__name__)
        CORS(self.app)
        self.llm = None
        self.email_service = None
        self.chat_agent = None
        self.email_agent = None
        self._init_services()
        self._register_routes()

    def _init_services(self):
        try:
            self.llm = LLMFactory.create(self.config.llm)
            self.chat_agent = ChatAgent(self.llm)
        except Exception as e:
            print(f"LLM init warning: {e}")
        try:
            self.email_service = EmailService(self.config.email)
            if self.llm:
                self.email_agent = EmailAgent(self.llm, self.email_service, self.config.agent)
        except Exception as e:
            print(f"Email service init warning: {e}")

    def _register_routes(self):
        app = self.app

        @app.route("/api/health", methods=["GET"])
        def health():
            return jsonify({
                "status": "ok",
                "service": "Email AI Agent",
                "version": "1.0.0",
                "llm_provider": self.config.llm.provider if self.llm else None,
                "email_enabled": self.email_service is not None,
            })

        @app.route("/api/chat/conversations", methods=["GET"])
        def list_conversations():
            if not self.chat_agent:
                return jsonify({"error": "Chat agent not available"}), 503
            return jsonify({"conversations": self.chat_agent.list_conversations()})

        @app.route("/api/chat/conversations", methods=["POST"])
        def create_conversation():
            if not self.chat_agent:
                return jsonify({"error": "Chat agent not available"}), 503
            data = request.get_json() or {}
            title = data.get("title", "")
            conv_id = self.chat_agent.create_conversation(title)
            return jsonify({"conversation_id": conv_id, "title": title}), 201

        @app.route("/api/chat/conversations/<conv_id>", methods=["DELETE"])
        def delete_conversation(conv_id):
            if not self.chat_agent:
                return jsonify({"error": "Chat agent not available"}), 503
            success = self.chat_agent.delete_conversation(conv_id)
            if success:
                return jsonify({"status": "deleted"})
            return jsonify({"error": "Conversation not found"}), 404

        @app.route("/api/chat/conversations/<conv_id>/messages", methods=["GET"])
        def get_messages(conv_id):
            if not self.chat_agent:
                return jsonify({"error": "Chat agent not available"}), 503
            conv = self.chat_agent.get_conversation(conv_id)
            if not conv:
                return jsonify({"error": "Conversation not found"}), 404
            return jsonify({
                "conversation_id": conv_id,
                "messages": [
                    {"role": m.role.value, "content": m.content}
                    for m in conv.messages
                    if m.role.value != "system"
                ],
            })

        @app.route("/api/chat/conversations/<conv_id>/send", methods=["POST"])
        def send_message(conv_id):
            if not self.chat_agent:
                return jsonify({"error": "Chat agent not available"}), 503
            data = request.get_json() or {}
            message = data.get("message", "")
            system_prompt = data.get("system_prompt")
            stream = data.get("stream", False)
            if not message:
                return jsonify({"error": "Message is required"}), 400
            if stream:
                def generate():
                    yield f"data: {json.dumps({'type': 'start', 'conversation_id': conv_id})}\n\n"
                    full_content = []
                    for chunk in self.chat_agent.send_message_stream(conv_id, message, system_prompt):
                        full_content.append(chunk)
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'content': ''.join(full_content)})}\n\n"
                import json
                return Response(stream_with_context(generate()), mimetype="text/event-stream")
            else:
                response = self.chat_agent.send_message(conv_id, message, system_prompt)
                return jsonify({
                    "conversation_id": conv_id,
                    "response": response,
                })

        @app.route("/api/email/inbox", methods=["GET"])
        def get_inbox():
            if not self.email_service:
                return jsonify({"error": "Email service not available"}), 503
            limit = int(request.args.get("limit", 20))
            unread_only = request.args.get("unread", "false").lower() == "true"
            emails = self.email_service.fetch_emails(limit=limit, unread_only=unread_only)
            return jsonify({
                "count": len(emails),
                "emails": [
                    {
                        "id": em.id,
                        "subject": em.subject,
                        "sender": em.sender,
                        "sender_name": em.sender_name,
                        "date": em.date.isoformat() if em.date else None,
                        "is_read": em.is_read,
                        "snippet": em.body[:100],
                    }
                    for em in emails
                ],
            })

        @app.route("/api/email/<email_id>", methods=["GET"])
        def get_email(email_id):
            if not self.email_service:
                return jsonify({"error": "Email service not available"}), 503
            emails = self.email_service.fetch_emails(limit=100)
            for em in emails:
                if em.id == email_id:
                    return jsonify({
                        "id": em.id,
                        "subject": em.subject,
                        "sender": em.sender,
                        "sender_name": em.sender_name,
                        "to": em.to,
                        "cc": em.cc,
                        "date": em.date.isoformat() if em.date else None,
                        "body": em.body,
                        "body_html": em.body_html,
                        "is_read": em.is_read,
                    })
            return jsonify({"error": "Email not found"}), 404

        @app.route("/api/email/<email_id>/analyze", methods=["GET"])
        def analyze_email(email_id):
            if not self.email_agent:
                return jsonify({"error": "Email agent not available"}), 503
            emails = self.email_service.fetch_emails(limit=100)
            target_email = None
            for em in emails:
                if em.id == email_id:
                    target_email = em
                    break
            if not target_email:
                return jsonify({"error": "Email not found"}), 404
            analysis = self.email_agent.analyze_email(target_email)
            if not analysis:
                return jsonify({"error": "Analysis failed"}), 500
            return jsonify({
                "email_id": email_id,
                "summary": analysis.summary,
                "category": analysis.category,
                "priority": analysis.priority,
                "key_points": analysis.key_points,
                "action_items": analysis.action_items,
                "sender_tone": analysis.sender_tone,
            })

        @app.route("/api/email/<email_id>/reply", methods=["POST"])
        def generate_reply(email_id):
            if not self.email_agent:
                return jsonify({"error": "Email agent not available"}), 503
            data = request.get_json() or {}
            instruction = data.get("instruction", "请礼貌地回复这封邮件")
            send = data.get("send", False)
            emails = self.email_service.fetch_emails(limit=100)
            target_email = None
            for em in emails:
                if em.id == email_id:
                    target_email = em
                    break
            if not target_email:
                return jsonify({"error": "Email not found"}), 404
            reply_body = self.email_agent.generate_reply(target_email, instruction)
            if send:
                success = self.email_agent.send_reply(target_email, reply_body)
                return jsonify({
                    "email_id": email_id,
                    "reply_body": reply_body,
                    "sent": success,
                })
            return jsonify({
                "email_id": email_id,
                "reply_body": reply_body,
                "sent": False,
            })

        @app.route("/api/email/send", methods=["POST"])
        def send_email():
            if not self.email_service:
                return jsonify({"error": "Email service not available"}), 503
            data = request.get_json() or {}
            to = data.get("to", [])
            subject = data.get("subject", "")
            body = data.get("body", "")
            cc = data.get("cc", [])
            if not to or not subject:
                return jsonify({"error": "to and subject are required"}), 400
            success = self.email_service.send_email(
                to=to if isinstance(to, list) else [to],
                subject=subject,
                body=body,
                cc=cc if isinstance(cc, list) else ([cc] if cc else []),
            )
            if success:
                return jsonify({"status": "sent"})
            return jsonify({"error": "Send failed"}), 500

        @app.route("/api/email/compose", methods=["POST"])
        def compose_email():
            if not self.email_agent:
                return jsonify({"error": "Email agent not available"}), 503
            data = request.get_json() or {}
            to = data.get("to", [])
            topic = data.get("topic", "")
            context = data.get("context", "")
            tone = data.get("tone", "professional")
            if not to or not topic:
                return jsonify({"error": "to and topic are required"}), 400
            result = self.email_agent.compose_email(
                to=to if isinstance(to, list) else [to],
                topic=topic,
                context=context,
                tone=tone,
            )
            return jsonify(result)

        @app.route("/api/email/summarize", methods=["GET"])
        def summarize_emails():
            if not self.email_agent:
                return jsonify({"error": "Email agent not available"}), 503
            limit = int(request.args.get("limit", 10))
            emails = self.email_service.fetch_emails(limit=limit)
            summary = self.email_agent.batch_summarize(emails)
            return jsonify({
                "count": len(emails),
                "summary": summary,
            })

        @app.route("/api/email/unread-count", methods=["GET"])
        def unread_count():
            if not self.email_service:
                return jsonify({"error": "Email service not available"}), 503
            count = self.email_service.get_unread_count()
            return jsonify({"unread_count": count})

        @app.route("/api/status", methods=["GET"])
        def status():
            return jsonify({
                "llm": {
                    "provider": self.config.llm.provider,
                    "model": self.config.llm.model,
                    "available": self.llm is not None,
                },
                "email": {
                    "address": self.config.email.address,
                    "available": self.email_service is not None,
                    "unread_count": self.email_service.get_unread_count() if self.email_service else 0,
                },
                "server": {
                    "host": self.config.server.host,
                    "port": self.config.server.port,
                },
            })

    def run(self, host: Optional[str] = None, port: Optional[int] = None, debug: Optional[bool] = None):
        host = host or self.config.server.host
        port = port or self.config.server.port
        debug = debug if debug is not None else self.config.server.debug
        print(f"Starting Email AI Agent server on {host}:{port}")
        print(f"API docs: http://{host}:{port}/api/health")
        self.app.run(host=host, port=port, debug=debug)
