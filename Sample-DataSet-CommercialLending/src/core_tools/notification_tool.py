import requests

class NotificationTool:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_notification(self, message: str):
        """
        Sends a notification to a chat webhook.

        Args:
            message: The message to send.
        """
        print(f"NotificationTool: Sending notification: {message}")
        # TODO: Implement the notification sending
        # response = requests.post(self.webhook_url, json={"text": message})
        # return response.status_code
        return 200
