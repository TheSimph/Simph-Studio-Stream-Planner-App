import requests

class DiscordClient:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url.strip() if webhook_url else ""
        self.base_webhook = self.webhook_url.split('?')[0].rstrip('/') if self.webhook_url else ""

    def delete_old_schedule(self, last_msg_id):
        if self.base_webhook and last_msg_id:
            try: 
                del_req = requests.delete(f"{self.base_webhook}/messages/{last_msg_id}", timeout=10)
                if del_req.status_code == 204:
                    return True, "Old schedule successfully deleted."
                else:
                    return False, f"Old schedule not found or couldn't be deleted (Code {del_req.status_code})."
            except Exception as e: 
                return False, f"Delete request failed: {e}"
        return False, "No webhook or message ID."

    def deploy_schedule(self, message_content, image_path):
        if self.base_webhook:
            try:
                with open(image_path, "rb") as f:
                    r = requests.post(
                        f"{self.base_webhook}?wait=true", 
                        data={"content": message_content}, 
                        files={"file": f}, 
                        timeout=15
                    )
                    if r.status_code in [200, 204]:
                        new_msg_id = ""
                        try:
                            new_msg_id = r.json().get("id", "")
                        except: 
                            pass
                        return True, new_msg_id, "Successfully Uploaded."
                    else:
                        return False, "", f"Upload failed with status code {r.status_code}."
            except Exception as e: 
                return False, "", f"Webhook Error: {e}"
        return False, "", "No webhook configured."