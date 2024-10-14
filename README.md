# Solana Hook

This is a Dokku service to listen transactions for a Solana address in real-time and publish the transaction to a webhook. This is an open-source replacement for Helius or Hello-Moon transaction webhooks.

This service uses automatic reconnection, heartbeats, and robust error handling.

## Dev Setup
- Rename .env.sample to .env and setup env vars
- `poetry install`
- `poetry run python main.py`

## Prod Deploy
- Setup env vars in Dokku following `.env.sample`
  - `dokku config:set my_app MY_VAR=MY_VALUE`
- Setup up poetry buildpack as 1 and Heroku python buildpack as 2
  - `dokku buildpack:add my_app --index 1 https://github.com/moneymeets/python-poetry-buildpack.git`
  - `dokku buildpack:add my_app --index 2 https://github.com/heroku/heroku-buildpack-python.git`
- Deploy
- Scale worker to at least 1
  - `dokku ps:scale my_app worker=1`
