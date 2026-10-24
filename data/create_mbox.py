import json
import mailbox
import os
import datetime
from email.message import EmailMessage
from email.utils import formatdate

json_path = os.path.join(os.path.dirname(__file__), "sample_inbox.json")
mbox_path = os.path.join(os.path.dirname(__file__), "sample_inbox.mbox")

if os.path.exists(mbox_path):
    os.remove(mbox_path)

with open(json_path, "r", encoding="utf-8") as f:
    emails = json.load(f)

mbox = mailbox.mbox(mbox_path)

for item in emails:
    msg = EmailMessage()
    msg["From"] = item["sender"]
    msg["To"] = item["recipient"]
    msg["Subject"] = item["subject"]
    msg["Message-ID"] = f"<{item['id']}@jobautopilot.local>"
    
    dt = datetime.datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
    msg["Date"] = formatdate(dt.timestamp())
    msg.set_content(item["body"], charset="utf-8")
    
    mbox.add(msg.as_bytes())

mbox.flush()
mbox.close()
print(f"Successfully generated {mbox_path} with {len(emails)} messages.")
