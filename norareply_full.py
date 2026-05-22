#!/usr/bin/env python3
"""
NoraReply FULL - Automated Customer Reply Tool for Climb NORA
Ready-to-use version with real email checking and replying.

SETUP INSTRUCTIONS ARE IN THE SEPARATE SETUP_GUIDE FILE.
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import time
import os
from datetime import datetime

# ============================================================
# ================== CONFIGURATION ==========================
# ============================================================
# Fill these in before running:

GMAIL_EMAIL = "hello@climbnora.com"          # <-- Change to the inbox you want to monitor
GMAIL_APP_PASSWORD = "your-app-password-here"  # <-- Use Gmail App Password (NOT your normal password)

CHECK_EVERY_SECONDS = 300                    # Check every 5 minutes (300 seconds)
DRY_RUN = False                              # Set to True to test without actually sending replies

# ============================================================
# ============== GYM INFORMATION (Edit as needed) ===========
# ============================================================

GYM_NAME = "Climb NORA"
GYM_PHONE = "(253) 200-1413"
GYM_ADDRESS = "30820 Pacific Hwy S, Federal Way, WA 98003"
GYM_WEBSITE = "https://climbnora.com"
GYM_INSTAGRAM = "@climb_nora"

HOURS = """Monday – Friday: 10:00 AM – 10:00 PM
Saturday – Sunday: 10:00 AM – 8:00 PM"""

PRICING = """• Day Pass: $21
• Weekly Membership: ~$21/week (flexible)
• Monthly: from $84/month
• Student discounts available
• Current Summer Pass: $190 (until Aug 1, 2026)"""

FIRST_TIME = """Welcome! 
- Sign a waiver (at desk or check website)
- Free Intro to Bouldering class available
- Comfortable clothes + closed toe shoes recommended
- We have shoe & chalk rentals"""

# ============================================================
# ================== CLASSIFICATION & REPLIES ===============
# ============================================================

def classify_intent(subject, body):
    text = f"{subject} {body}".lower()
    
    first_time_kws = ["first time", "first timer", "beginner", "never climbed", "intro", "waiver", "what do i need", "bring", "rentals"]
    if any(kw in text for kw in first_time_kws):
        return "first_time"
    
    hours_kws = ["hour", "hours", "open", "close", "what time", "schedule"]
    if any(kw in text for kw in hours_kws):
        return "hours"
    
    pricing_kws = ["price", "cost", "how much", "day pass", "membership", "$", "promo", "summer pass"]
    if any(kw in text for kw in pricing_kws):
        return "pricing"
    
    youth_kws = ["youth", "kid", "kids", "child", "teen", "program"]
    if any(kw in text for kw in youth_kws):
        return "youth"
    
    location_kws = ["address", "location", "where", "directions", "parking"]
    if any(kw in text for kw in location_kws):
        return "location"
    
    return "general"


def get_reply(intent, sender_name="there"):
    if intent == "hours":
        return f"""Hi {sender_name},

Thanks for checking our hours!

{HOURS}

We're at {GYM_ADDRESS}.

{sign_off()}"""

    elif intent == "pricing":
        return f"""Hi {sender_name},

Here’s our current pricing:

{PRICING}

We also offer a FREE Intro to Bouldering class.

{sign_off()}"""

    elif intent == "first_time":
        return f"""Hi {sender_name},

Awesome — welcome to Climb NORA! 🧗

{FIRST_TIME}

Come on in, we’ll take care of you.

{sign_off()}"""

    elif intent == "youth":
        return f"""Hi {sender_name},

Yes! We have youth programs.

Check climbnora.com/youth or reply here for current details.

{sign_off()}"""

    elif intent == "location":
        return f"""Hi {sender_name},

We’re located at:
{GYM_ADDRESS}

{sign_off()}"""

    else:
        return f"""Hi {sender_name},

Thanks for reaching out to Climb NORA!

Quick info:
- Hours: {HOURS.replace(chr(10), ' | ')}
- Day Pass: $21
- Beginner friendly with great community

Reply with your specific question or call us at {GYM_PHONE}.

{sign_off()}"""


def sign_off():
    return f"""Thanks!
Climb NORA Team
{GYM_PHONE} | {GYM_WEBSITE}
{GYM_INSTAGRAM}"""


def extract_name(body):
    import re
    match = re.search(r"(?:hi|hello|hey)\s+([A-Za-z]+)", body, re.IGNORECASE)
    return match.group(1).capitalize() if match else "there"


# ============================================================
# ================== EMAIL FUNCTIONS ========================
# ============================================================

def connect_imap():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
    mail.select("inbox")
    return mail


def send_reply(to_email, subject, body, original_msg_id=None):
    if DRY_RUN:
        print(f"[DRY RUN] Would send reply to {to_email}")
        return

    msg = MIMEMultipart()
    msg["From"] = GMAIL_EMAIL
    msg["To"] = to_email
    msg["Subject"] = f"Re: {subject}"
    
    if original_msg_id:
        msg["In-Reply-To"] = original_msg_id
        msg["References"] = original_msg_id

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)


def process_emails():
    print(f"\n[{datetime.now()}] Checking inbox...")
    try:
        mail = connect_imap()
        status, messages = mail.search(None, "UNSEEN")
        
        if status != "OK" or not messages[0]:
            print("No new emails.")
            mail.logout()
            return

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} new email(s).")

        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()

            from_email = msg.get("From")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            intent = classify_intent(subject, body)
            name = extract_name(body)
            reply_body = get_reply(intent, name)

            print(f"→ Replying to {from_email} | Intent: {intent}")

            if not DRY_RUN:
                send_reply(from_email, subject, reply_body, msg.get("Message-ID"))
                mail.store(email_id, "+FLAGS", "\\Seen")

        mail.logout()
        print("Done processing.")

    except Exception as e:
        print(f"Error: {e}")


# ============================================================
# ====================== MAIN LOOP ==========================
# ============================================================

if __name__ == "__main__":
    print("=== NoraReply FULL is starting ===")
    print(f"Monitoring: {GMAIL_EMAIL}")
    print(f"Check interval: {CHECK_EVERY_SECONDS} seconds")
    print(f"Dry Run Mode: {DRY_RUN}")
    print("Press Ctrl+C to stop.\n")

    while True:
        process_emails()
        time.sleep(CHECK_EVERY_SECONDS)