import os
import mailbox
import email
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import List, Optional, Dict
import logging
import re
from bs4 import BeautifulSoup
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PIIRedactor:
    
    def __init__(self):
        try:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            logger.info("Using Presidio for PII redaction")
        except Exception as e:
            logger.error(f"Failed to initialize Presidio: {e}")
            raise
        
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b')
        self.ssn_pattern = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        self.sin_pattern = re.compile(r'\b\d{3}[-\s]?\d{3}[-\s]?\d{3}\b')
        self.postal_code_pattern = re.compile(r'\b[A-Z]\d[A-Z][-\s]?\d[A-Z]\d\b', re.IGNORECASE)
        self.credit_card_pattern = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')
        self.address_pattern = re.compile(r'\b\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|way|court|ct)\.?\b', re.IGNORECASE)
        
        self.mortgage_amount_pattern = re.compile(r'\$?\s?[\d,]+\.?\d*[kKmM]?(?=\s|$|\.|\,)', re.IGNORECASE)
        self.interest_rate_pattern = re.compile(r'\b\d+\.?\d*\s?%(?:\s+(?:variable|fixed|APR|rate))?', re.IGNORECASE)
        self.income_pattern = re.compile(r'\$?\s?\d{2,3}[,\s]?\d{3}[kK]?(?=\s|$|\.|\,)', re.IGNORECASE)
        self.large_number_pattern = re.compile(r'\b\d{4,}(?:,\d{3})*\b')
        
        self.bc_cities = [
            'Vancouver', 'Burnaby', 'Surrey', 'Richmond', 'Delta', 'Langley', 
            'Coquitlam', 'Abbotsford', 'North Vancouver', 'West Vancouver', 
            'Chilliwack', 'Kelowna', 'Victoria', 'Kamloops', 'Nanaimo', 
            'Prince George', 'New Westminster', 'Port Coquitlam', 'Maple Ridge',
            'Pitt Meadows', 'White Rock', 'Port Moody', 'Mission', 'Squamish'
        ]
        self.city_pattern = re.compile(r'\b(' + '|'.join(self.bc_cities) + r')\b', re.IGNORECASE)
        
        self.job_titles = [
            'engineer', 'developer', 'analyst', 'contractor', 'teacher', 'nurse',
            'supervisor', 'manager', 'technician', 'accountant', 'architect',
            'consultant', 'designer', 'director', 'specialist', 'coordinator',
            'administrator', 'lawyer', 'doctor', 'physician', 'dentist', 'pharmacist',
            'electrician', 'plumber', 'mechanic', 'carpenter', 'realtor', 'agent',
            'sales', 'representative', 'assistant', 'clerk', 'officer', 'executive',
            'president', 'ceo', 'cto', 'cfo', 'vp', 'vice president'
        ]
        self.job_title_pattern = re.compile(r'\b(' + '|'.join(self.job_titles) + r')s?\b', re.IGNORECASE)
        
        self.employer_pattern = re.compile(
            r'(?:work|works|working|worked|employed|employee)\s+(?:at|with|for|by)\s+([A-Z][A-Za-z0-9\s&\.,]+?)(?=\s+(?:as|in|since|for|and|but|or|\.|,|$))',
            re.IGNORECASE
        )
        
        self.date_pattern = re.compile(
            r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|'
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}|'
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',
            re.IGNORECASE
        )
        
        self.message_id_pattern = re.compile(r'<[^>]+@[^>]+>')
        
        self.forwarded_header_pattern = re.compile(
            r'^(?:From|To|Cc|Bcc|Sent|Date|Subject|Forwarded message|Original message|Begin forwarded message):',
            re.IGNORECASE | re.MULTILINE
        )
    
    def redact_with_presidio(self, text: str) -> str:
        try:
            results = self.analyzer.analyze(
                text=text,
                language='en',
                entities=[
                    "PHONE_NUMBER", "EMAIL_ADDRESS", "PERSON", 
                    "LOCATION", "CREDIT_CARD", "US_SSN", 
                    "DATE_TIME", "IP_ADDRESS", "URL"
                ]
            )
            
            anonymized = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={"DEFAULT": {"type": "replace", "new_value": "[REDACTED]"}}
            )
            
            redacted_text = anonymized.text
            redacted_text = self._apply_mortgage_patterns(redacted_text)
            
            return redacted_text
        except Exception as e:
            logger.error(f"Presidio redaction failed: {e}")
            return self.redact_with_regex(text)
    
    def redact_with_regex(self, text: str) -> str:
        text = self.email_pattern.sub('[EMAIL]', text)
        text = self.phone_pattern.sub('[PHONE]', text)
        text = self.ssn_pattern.sub('[SSN]', text)
        text = self.sin_pattern.sub('[SIN]', text)
        text = self.postal_code_pattern.sub('[POSTAL_CODE]', text)
        text = self.credit_card_pattern.sub('[CREDIT_CARD]', text)
        text = self.address_pattern.sub('[ADDRESS]', text)
        text = self._apply_mortgage_patterns(text)
        
        return text
    
    def _apply_mortgage_patterns(self, text: str) -> str:
        text = self.date_pattern.sub('[DATE]', text)
        text = self.message_id_pattern.sub('[MSG_ID]', text)
        text = self.mortgage_amount_pattern.sub('[AMOUNT]', text)
        text = self.interest_rate_pattern.sub('[RATE]', text)
        text = self.income_pattern.sub('[INCOME]', text)
        text = self.city_pattern.sub('[CITY]', text)
        text = self.job_title_pattern.sub('[JOB_TITLE]', text)
        text = self.employer_pattern.sub('[EMPLOYER]', text)
        text = self.large_number_pattern.sub('[NUMBER]', text)
        
        return text
    
    def sanitize_line_by_line(self, text: str) -> str:
        lines = text.split('\n')
        sanitized_lines = []
        
        for line in lines:
            if self.forwarded_header_pattern.match(line.strip()):
                continue
            
            line = self.email_pattern.sub('[EMAIL]', line)
            line = self.phone_pattern.sub('[PHONE]', line)
            line = self.date_pattern.sub('[DATE]', line)
            line = self.message_id_pattern.sub('[MSG_ID]', line)
            line = self._apply_mortgage_patterns(line)
            
            sanitized_lines.append(line)
        
        return '\n'.join(sanitized_lines)
    
    def redact(self, text: str) -> str:
        redacted = self.redact_with_presidio(text)
        redacted = self.sanitize_line_by_line(redacted)
        return redacted


class EmailProcessor:
    
    def __init__(self, redact_pii: bool = True):
        self.output_dir = config.RAW_DOCS_DIR
        self.redact_pii = redact_pii
        self.redactor = PIIRedactor() if redact_pii else None
        # Agent emails MUST be provided via environment variable AGENT_EMAILS (comma-separated)
        agent_env = config.AGENT_EMAILS
        if not agent_env:
            raise ValueError(
                "AGENT_EMAILS environment variable is required and must contain agent email(s) separated by commas.\n"
                "Example: export AGENT_EMAILS='dad@company.com,dad+alias@company.com'"
            )
        # parse and normalize
        self.agent_emails = [e.strip().lower() for e in agent_env.split(',') if e.strip()]
        if not self.agent_emails:
            raise ValueError("AGENT_EMAILS parsed to an empty list; provide at least one email address.")
    
    def process_mbox_file(self, mbox_path: Path) -> List[Dict[str, str]]:
        try:
            mbox = mailbox.mbox(str(mbox_path))
            emails_data = []
            
            logger.info(f"Processing mbox file: {mbox_path.name}")
            
            for idx, message in enumerate(mbox):
                try:
                    subject = message.get('subject', 'No Subject')
                    from_addr = message.get('from', 'Unknown')
                    to_addr = message.get('to', 'Unknown')
                    date = message.get('date', 'Unknown')
                    message_id = message.get('message-id') or message.get('Message-ID') or ''
                    in_reply_to = message.get('in-reply-to') or message.get('In-Reply-To') or ''
                    references = message.get('references') or ''
                    
                    body = ""
                    if message.is_multipart():
                        for part in message.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get('Content-Disposition', ''))
                            
                            if 'attachment' in content_disposition:
                                continue
                            
                            if content_type == "text/plain":
                                try:
                                    payload = part.get_payload(decode=True)
                                    body += payload.decode('utf-8', errors='ignore')
                                except:
                                    try:
                                        body += payload.decode('latin-1', errors='ignore')
                                    except:
                                        pass
                            elif content_type == "text/html" and not body:
                                try:
                                    payload = part.get_payload(decode=True)
                                    html_content = payload.decode('utf-8', errors='ignore')
                                    soup = BeautifulSoup(html_content, 'html.parser')
                                    body += soup.get_text()
                                except:
                                    pass
                    else:
                        try:
                            payload = message.get_payload(decode=True)
                            if payload:
                                body = payload.decode('utf-8', errors='ignore')
                        except:
                            body = str(message.get_payload())
                    
                    # Determine role (agent vs client) and whether this is a reply
                    role = self._determine_role(from_addr, to_addr)
                    is_reply = bool(in_reply_to) or subject.strip().lower().startswith('re:')
                    thread_id = self._derive_thread_id(message_id, in_reply_to, references, subject)

                    if self.redact_pii and self.redactor:
                        subject = self.redactor.redact(subject)
                        body = self.redactor.redact(body)
                        from_addr = self.redactor.redact(from_addr)
                        to_addr = self.redactor.redact(to_addr)
                    
                    redacted_thread_id = self.redactor.redact(thread_id) if self.redact_pii and self.redactor else '[THREAD_ID]'
                    
                    content = f"""EMAIL MESSAGE {idx + 1}
=============
Subject: {subject}
From: {from_addr}
To: {to_addr}
Date: [DATE]
Thread-ID: {redacted_thread_id}
Role: {role}
Is-Reply: {is_reply}

{body}

---
"""
                    
                    emails_data.append({
                        'content': content,
                        'subject': subject,
                        'index': idx,
                        'message_id': message_id,
                        'in_reply_to': in_reply_to,
                        'references': references,
                        'role': role,
                        'is_reply': is_reply,
                        'thread_id': thread_id
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing email {idx} in {mbox_path.name}: {e}")
                    continue
            
            logger.info(f"Processed {len(emails_data)} emails from {mbox_path.name}")
            return emails_data
            
        except Exception as e:
            logger.error(f"Error processing mbox file {mbox_path}: {e}")
            return []
    
    def convert_mbox_to_txt(self, mbox_path: Path, output_path: Optional[Path] = None, batch_size: int = 50):
        emails_data = self.process_mbox_file(mbox_path)
        
        if not emails_data:
            logger.warning(f"No emails extracted from {mbox_path.name}")
            return
        
        batch_num = 0
        for i in range(0, len(emails_data), batch_size):
            batch = emails_data[i:i + batch_size]
            batch_num += 1
            
            if output_path:
                out_path = output_path.parent / f"{output_path.stem}_batch{batch_num}.txt"
            else:
                out_path = self.output_dir / f"{mbox_path.stem}_batch{batch_num}.txt"
            
            combined_content = f"EMAIL BATCH {batch_num} from {mbox_path.name}\n"
            combined_content += "=" * 60 + "\n\n"
            combined_content += "\n\n".join([email['content'] for email in batch])
            
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(combined_content)
            
            logger.info(f"Saved batch {batch_num} ({len(batch)} emails) -> {out_path.name}")
        
        logger.info(f"Converted {mbox_path.name} -> {batch_num} batch file(s)")
    
    def process_eml_file(self, eml_path: Path) -> str:
        try:
            with open(eml_path, 'rb') as f:
                msg = BytesParser(policy=policy.default).parse(f)
            
            subject = msg.get('subject', 'No Subject')
            from_addr = msg.get('from', 'Unknown')
            to_addr = msg.get('to', 'Unknown')
            date = msg.get('date', 'Unknown')
            message_id = msg.get('message-id') or msg.get('Message-ID') or ''
            in_reply_to = msg.get('in-reply-to') or msg.get('In-Reply-To') or ''
            references = msg.get('references') or ''
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))
                    
                    if 'attachment' in content_disposition:
                        continue
                    
                    if content_type == "text/plain":
                        try:
                            body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except:
                            body += part.get_payload(decode=True).decode('latin-1', errors='ignore')
                    elif content_type == "text/html" and not body:
                        try:
                            html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            soup = BeautifulSoup(html_content, 'html.parser')
                            body += soup.get_text()
                        except:
                            pass
            else:
                try:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    body = msg.get_payload(decode=True).decode('latin-1', errors='ignore')
            role = self._determine_role(from_addr, to_addr)
            is_reply = bool(in_reply_to) or subject.strip().lower().startswith('re:')
            thread_id = self._derive_thread_id(message_id, in_reply_to, references, subject)

            if self.redact_pii and self.redactor:
                subject = self.redactor.redact(subject)
                body = self.redactor.redact(body)
                from_addr = self.redactor.redact(from_addr)
                to_addr = self.redactor.redact(to_addr)

            redacted_thread_id = self.redactor.redact(thread_id) if self.redact_pii and self.redactor else '[THREAD_ID]'

            content = f"""EMAIL MESSAGE
=============
Subject: {subject}
From: {from_addr}
To: {to_addr}
Date: [DATE]
Thread-ID: {redacted_thread_id}
Role: {role}
Is-Reply: {is_reply}

{body}
"""
            
            return content
            
        except Exception as e:
            logger.error(f"Error processing email {eml_path}: {e}")
            return ""
    
    def convert_eml_to_txt(self, eml_path: Path, output_path: Optional[Path] = None):
        content = self.process_eml_file(eml_path)
        
        if not content:
            return
        
        if not output_path:
            output_path = self.output_dir / f"{eml_path.stem}.txt"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Converted {eml_path.name} -> {output_path.name}")
    
    def batch_convert_emails(self, email_dir: Path):
        mbox_files = list(email_dir.glob("*.mbox"))
        eml_files = list(email_dir.glob("*.eml"))
        
        if not mbox_files and not eml_files:
            logger.warning(f"No email files found in {email_dir}")
            return
        
        if mbox_files:
            logger.info(f"Found {len(mbox_files)} mbox file(s)")
            for mbox_file in mbox_files:
                try:
                    self.convert_mbox_to_txt(mbox_file)
                except Exception as e:
                    logger.error(f"Failed to convert {mbox_file}: {e}")
        
        if eml_files:
            logger.info(f"Found {len(eml_files)} .eml file(s)")
            for eml_file in eml_files:
                try:
                    self.convert_eml_to_txt(eml_file)
                except Exception as e:
                    logger.error(f"Failed to convert {eml_file}: {e}")
        
        logger.info(f"Email conversion complete!")

    def _determine_role(self, from_header: str, to_header: str) -> str:
        """Return 'agent' if sender matches known agent emails, 'client' if not, or 'unknown'."""
        try:
            from_l = (from_header or '').lower()
            to_l = (to_header or '').lower()
            # match any agent email substring
            for agent in self.agent_emails:
                if agent and agent in from_l:
                    return 'agent'
                if agent and agent in to_l:
                    # if agent is in recipients, sender likely client
                    return 'client'
            # heuristics: if 'on behalf of' or 'via' appears, try to infer
            if 'on behalf of' in from_l or 'via' in from_l:
                return 'client'
            # fallback: if 'noreply' or 'no-reply' in from, treat as client/outbound
            if 'noreply' in from_l or 'no-reply' in from_l:
                return 'client'
            return 'unknown'
        except Exception:
            return 'unknown'

    def _derive_thread_id(self, message_id: str, in_reply_to: str, references: str, subject: str) -> str:
        """Derive a stable thread id using In-Reply-To/References or normalized subject as fallback."""
        # Prefer In-Reply-To or References message ids
        if in_reply_to:
            return self._normalize_msg_id(in_reply_to)
        if references:
            # references may contain multiple ids; use the first
            first_ref = references.split()[0]
            return self._normalize_msg_id(first_ref)
        if message_id:
            return self._normalize_msg_id(message_id)
        # fallback to normalized subject (strip Re:/Fwd:)
        subj = subject.lower()
        subj = re.sub(r'^(re:|fwd:|fw:)+\s*', '', subj)
        subj = re.sub(r'[^a-z0-9]+', '_', subj).strip('_')
        return f"subject::{subj[:120]}"

    def _normalize_msg_id(self, msg_id: str) -> str:
        if not msg_id:
            return ''
        # strip angle brackets and whitespace
        return msg_id.strip().lstrip('<').rstrip('>').strip()


if __name__ == "__main__":
    processor = EmailProcessor(redact_pii=True)
    
    email_folder = Path("path/to/google/takeout/Mail")
    
    if email_folder.exists():
        processor.batch_convert_emails(email_folder)
    else:
        logger.info("Please update email_folder path to your Google Takeout Mail directory")
        logger.info("Example: Path('C:/Users/YourName/Downloads/Takeout/Mail')")

