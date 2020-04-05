# supermarket_checker_bot
This Telegram bot is a Google Cloud function for reporting and checking the crowd levels at supermarkets. PostgreSQL on GCP is used as well.

# Deployment
1. Install Google Cloud SDK.
https://cloud.google.com/sdk/docs/downloads-interactive

2. Deploy this bot to GCP using the gcloud tool. 
<pre> gcloud functions deploy webhook --env-vars-file env.yml --runtime python37 --trigger-http --allow-unauthenticated </pre>

3. Call the setWebHook method in the Bot API via the following url:
https://api.telegram.org/bot{my_bot_token}/setWebhook?url={url_to_send_updates_to}.

Webhook has been set, do not need to re-set. Just run 2. to update bot.
