# Phenesty AI Video Studio

A responsive prompt-to-video website using a hosted AI text-to-video provider. The website runs locally on Windows; actual video inference is requested from the cloud, so the laptop does not need to load the video model into its 8 GB RAM.

## Start on Windows

1. Install Python 3.10+ if needed.
2. Follow the one-time token configuration in `SETUP_FREE_AI.md`.
3. Double-click `START_VIDEO_STUDIO.bat`.
4. Open `http://127.0.0.1:5000` in Chrome and keep the black command window open.

## Free-only policy and limitations

Hosted video generation is not guaranteed to be free or available. Hugging Face currently documents a small monthly free allowance for Inference Providers, subject to change, and it may not cover a video request. Do not add payment details or buy credits if you require zero cost. When the model cannot run, the app reports an error; it no longer generates a fake video with the prompt written on it.

## Configuration

Create a `.env` file based on `.env.example`, set `HF_TOKEN` to a Hugging Face token with inference permissions, and keep the token private. Provider/model can be changed using `HF_VIDEO_PROVIDER` and `HF_VIDEO_MODEL`.

## Safety and scope

- The server listens only on `127.0.0.1` by default.
- The token stays in the local backend `.env` file and is not sent to the browser.
- This is a development prototype, not a public multi-user production service.
- The chosen provider/model may limit duration, aspect ratio, output quality, or availability.
