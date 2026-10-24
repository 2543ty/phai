# Phenesty AI Video Studio

A Flask prompt-to-video app using a hosted Hugging Face Inference Provider. Video generation requires a valid Hugging Face token and a provider/model that supports text-to-video.

## Deploy on Render

This repository includes a `render.yaml` Blueprint configuration. In Render, choose **New + → Blueprint** and select this repository. The service uses:

- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app`
- Health check: `/api/health`

When Render asks for `HF_TOKEN`, enter it in Render's environment settings. **Never commit your token or put it in frontend code.** The `render.yaml` marks it as a secret (sync false), so it must be set privately in Render.

## Important free-tier limitations

Render's free web service may sleep when idle and has limited resources. Hosted AI inference is not guaranteed to be free or available; provider credits and model access are controlled by Hugging Face/provider. If inference fails, the app reports an error rather than substituting a fake video.

## Local Windows use

1. Install Python 3.10+.
2. Copy `.env.example` to `.env` and configure `HF_TOKEN` locally.
3. Run `START_VIDEO_STUDIO.bat`.
4. Visit `http://127.0.0.1:5000`.

Do not commit `.env`, generated MP4 files, virtual environments, or private tokens.
