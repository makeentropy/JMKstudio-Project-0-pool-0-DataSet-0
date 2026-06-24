import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from email.utils import parseaddr, formataddr
from typing import List, Dict, Optional, Tuple
import re
from bs4 import BeautifulSoup
from datetime import datetime
import ssl


class EmailMessage:
    def __init__(self):
        self.id: str = ""
        self.subject: str = ""
        self.sender: str = ""
        self.sender_name: str = ""
        self.to: List[str] = []
        self.cc: List[str] = []
        self.date: Optional[datetime] = None
        self.body: str = ""
        self.body_html: str = ""
        self.is_read: bool = False
        self.attachments: List[Dict] = []
        self.thread_id: str = ""

    def __repr__(self):
        return f"<EmailMessage id={self.id} subject='{self.subject}' from='{self.sender}'>"


class EmailService:
    def __init__(self, config):
        self.config = config
        self._imap = None
        self._smtp = None

    def _decode_str(self, s: str) -> str:
        if not s:
            return ""
        decoded_parts = decode_header(s)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(part)
        return "".join(result)

    def _parse_email_body(self, msg: email.message.Message) -> Tuple[str, str]:
        text_body = ""
        html_body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                if "attachment" in content_disposition:
                    continue
                try:
                    payload = part.get_payload(decode=True)
                    if payload is None:
                        continue
                    charset = part.get_content_charset() or "utf-8"
                    if content_type == "text/plain":
                        text_body += payload.decode(charset, errors="replace")
                    elif content_type == "text/html":
                        html_body += payload.decode(charset, errors="replace")
                except Exception:
                    continue
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                if content_type == "text/plain":
                    text_body = payload.decode(charset, errors="replace")
                elif content_type == "text/html":
                    html_body = payload.decode(charset, errors="replace")
        if not text_body and html_body:
            try:
                soup = BeautifulSoup(html_body, "html.parser")
                text_body = soup.get_text(separator="\n", strip=True)
            except Exception:
                text_body = html_body
        return text_body.strip(), html_body.strip()

    def connect_imap(self) -> bool:
        try:
            if self.config.use_ssl:
                context = ssl.create_default_context()
                self._imap = imaplib.IMAP4_SSL(
                    self.config.imap_server,
                    self.config.imap_port,
                    ssl_context=context,
                )
            else:
                self._imap = imaplib.IMAP4(self.config.imap_server, self.config.imap_port)
            self._imap.login(self.config.address, self.config.password)
            return True
        except Exception as e:
            print(f"IMAP connection failed: {e}")
            return False

    def disconnect_imap(self):
        if self._imap:
            try:
                self._imap.logout()
            except Exception:
                pass
            self._imap = None

    def connect_smtp(self) -> bool:
        try:
            if self.config.use_ssl:
                context = ssl.create_default_context()
                self._smtp = smtplib.SMTP_SSL(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    context=context,
                )
            else:
                self._smtp = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
                self._smtp.starttls()
            self._smtp.login(self.config.address, self.config.password)
            return True
        except Exception as e:
            print(f"SMTP connection failed: {e}")
            return False

    def disconnect_smtp(self):
        if self._smtp:
            try:
                self._smtp.quit()
            except Exception:
                pass
            self._smtp = None

    def list_folders(self) -> List[str]:
        if not self._imap and not self.connect_imap():
            return []
        try:
            status, folders = self._imap.list()
            if status != "OK":
                return []
            result = []
            for folder in folders:
                if isinstance(folder, bytes):
                    folder = folder.decode("utf-8", errors="replace")
                parts = folder.split(' "/" ')
                if len(parts) >= 2:
                    result.append(parts[1].strip('"'))
            return result
        except Exception as e:
            print(f"List folders failed: {e}")
            return []

    def fetch_emails(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        unread_only: bool = False,
    ) -> List[EmailMessage]:
        if not self._imap and not self.connect_imap():
            return []
        try:
            status, _ = self._imap.select(folder)
            if status != "OK":
                return []
            search_criteria = "ALL"
            if unread_only:
                search_criteria = "UNSEEN"
            status, data = self._imap.search(None, search_criteria)
            if status != "OK":
                return []
            email_ids = data[0].split()
            email_ids = email_ids[-limit:] if limit else email_ids
            emails = []
            for eid in reversed(email_ids):
                msg = self._fetch_single_email(eid)
                if msg:
                    emails.append(msg)
            return emails
        except Exception as e:
            print(f"Fetch emails failed: {e}")
            return []

    def _fetch_single_email(self, email_id: bytes) -> Optional[EmailMessage]:
        try:
            status, msg_data = self._imap.fetch(email_id, "(RFC822 FLAGS)")
            if status != "OK" or not msg_data:
                return None
            flags_str = ""
            raw_email = None
            for item in msg_data:
                if isinstance(item, tuple) and len(item) >= 2:
                    if item[0].endswith(b"RFC822"):
                        raw_email = item[1]
                    elif b"FLAGS" in item[0]:
                        flags_str = item[0].decode("utf-8", errors="replace")
            if not raw_email:
                for part in msg_data:
                    if isinstance(part, tuple) and len(part) >= 2:
                        if isinstance(part[1], bytes):
                            raw_email = part[1]
                            break
            if not raw_email:
                return None
            msg = email.message_from_bytes(raw_email)
            email_msg = EmailMessage()
            email_msg.id = email_id.decode("utf-8", errors="replace")
            email_msg.subject = self._decode_str(msg.get("Subject", ""))
            from_raw = msg.get("From", "")
            email_msg.sender_name, email_msg.sender = parseaddr(self._decode_str(from_raw))
            to_raw = msg.get("To", "")
            email_msg.to = [addr for _, addr in [parseaddr(self._decode_str(t.strip())) for t in to_raw.split(",") if t.strip()] if addr]
            cc_raw = msg.get("Cc", "")
            if cc_raw:
                email_msg.cc = [addr for _, addr in [parseaddr(self._decode_str(c.strip())) for c in cc_raw.split(",") if c.strip()] if addr]
            date_str = msg.get("Date", "")
            if date_str:
                try:
                    email_msg.date = email.utils.parsedate_to_datetime(date_str)
                except Exception:
                    pass
            email_msg.body, email_msg.body_html = self._parse_email_body(msg)
            email_msg.is_read = "\\Seen" in flags_str
            references = msg.get("References", "") or msg.get("In-Reply-To", "")
            if references:
                email_msg.thread_id = references.split()[0] if references.split() else email_msg.id
            else:
                email_msg.thread_id = email_msg.id
            return email_msg
        except Exception as e:
            print(f"Fetch email {email_id} failed: {e}")
            return None

    def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        html_body: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
    ) -> bool:
        if not self._smtp and not self.connect_smtp():
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = formataddr((self._decode_str("Email AI Assistant"), self.config.address))
            msg["To"] = ", ".join(to)
            if cc:
                msg["Cc"] = ", ".join(cc)
            msg["Subject"] = self._decode_str(subject)
            if in_reply_to:
                msg["In-Reply-To"] = in_reply_to
            if references:
                msg["References"] = references
            text_part = MIMEText(body, "plain", "utf-8")
            msg.attach(text_part)
            if html_body:
                html_part = MIMEText(html_body, "html", "utf-8")
                msg.attach(html_part)
            all_recipients = to + (cc or [])
            self._smtp.sendmail(self.config.address, all_recipients, msg.as_string())
            return True
        except Exception as e:
            print(f"Send email failed: {e}")
            return False

    def mark_as_read(self, email_id: str, folder: str = "INBOX") -> bool:
        if not self._imap and not self.connect_imap():
            return False
        try:
            self._imap.select(folder)
            self._imap.store(email_id, "+FLAGS", "\\Seen")
            return True
        except Exception as e:
            print(f"Mark as read failed: {e}")
            return False

    def search_emails(
        self,
        keyword: str,
        folder: str = "INBOX",
        limit: int = 20,
    ) -> List[EmailMessage]:
        if not self._imap and not self.connect_imap():
            return []
        try:
            self._imap.select(folder)
            status, data = self._imap.search(None, f'SUBJECT "{keyword}"')
            if status != "OK":
                return []
            email_ids = data[0].split()[-limit:] if limit else data[0].split()
            emails = []
            for eid in reversed(email_ids):
                msg = self._fetch_single_email(eid)
                if msg:
                    emails.append(msg)
            return emails
        except Exception as e:
            print(f"Search emails failed: {e}")
            return []

    def get_unread_count(self, folder: str = "INBOX") -> int:
        if not self._imap and not self.connect_imap():
            return 0
        try:
            self._imap.select(folder)
            status, data = self._imap.search(None, "UNSEEN")
            if status != "OK":
                return 0
            return len(data[0].split())
        except Exception as e:
            print(f"Get unread count failed: {e}")
            return 0
