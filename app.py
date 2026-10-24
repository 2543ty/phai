from flask import Flask, request, jsonify, send_from_directory, abort
from pathlib import Path
from dotenv import load_dotenv
import threading, json, uuid, re, os, shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA = ROOT / "data"
OUTPUT = ROOT / "generated"
for folder in (DATA, OUTPUT):
    folder.mkdir(exist_ok=True)
load_dotenv(ROOT / ".env")
MAGIC_HOUR_API_KEY = os.getenv("MAGIC_HOUR_API_KEY", "").strip()
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
HF_MODEL = os.getenv("HF_VIDEO_MODEL", "Wan-AI/Wan2.2-TI2V-5B").strip()
HF_PROVIDER = os.getenv("HF_VIDEO_PROVIDER", "fal-ai").strip()
JOBS_FILE = DATA / "jobs.json"
app = Flask(__name__, static_folder="static")

jobs_lock = threading.Lock()
jobs = {}
active_generation_lock = threading.Lock()

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def load_jobs():
    if JOBS_FILE.exists():
        try:
            saved = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
            for job in saved[-50:]:
                if job.get("status") in ("processing", "queued"):
                    job["status"] = "failed"
                    job["error"] = "Server restarted before generation finished. Please try again."
                jobs[job["id"]] = job
        except (json.JSONDecodeError, OSError):
            pass

def save_jobs():
    with jobs_lock:
        payload = sorted(jobs.values(), key=lambda x: x.get("created_at", ""), reverse=True)[:50]
        JOBS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

load_jobs()

def make_video_with_hosted_model(job):
    """Prefer Magic Hour's limited trial-credit API; retain Hugging Face as fallback."""
    filename = f"{job['id']}.mp4"

    if MAGIC_HOUR_API_KEY:
        from magic_hour import Client

        client = Client(token=MAGIC_HOUR_API_KEY)
        result = client.v1.text_to_video.generate(
            end_seconds=5,
            aspect_ratio=job["aspect_ratio"],
            style={"prompt": f"{job['prompt']}. {job['style']} style, smooth camera motion, no text overlay."},
            name=f"Phenesty AI Video {job['id']}",
            model="ltx-2.5",
            resolution="480p",
            wait_for_completion=True,
            download_outputs=True,
            download_directory=str(OUTPUT),
        )
        if getattr(result, "status", None) != "complete":
            error = getattr(result, "error", None)
            detail = getattr(error, "message", None) if error else None
            raise RuntimeError(detail or f"Magic Hour generation ended with status: {getattr(result, 'status', 'unknown')}. Check trial credits and model availability.")
        paths = getattr(result, "downloaded_paths", None) or []
        if not paths:
            raise RuntimeError("Magic Hour reported completion but did not return a downloaded video file.")
        source = Path(str(paths[0]))
        if not source.is_file() or source.stat().st_size < 1024:
            raise RuntimeError("Magic Hour completed but the downloaded video file was missing or invalid.")
        destination = OUTPUT / filename
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        return filename

    if not HF_TOKEN:
        raise RuntimeError("No video provider is configured. Add MAGIC_HOUR_API_KEY to use Magic Hour trial credits, or configure Hugging Face inference.")

    from huggingface_hub import InferenceClient
    style_words = {
        "cinematic": "cinematic camera movement, realistic lighting, detailed scene",
        "animation": "stylized animation, smooth motion, expressive colors",
        "documentary": "natural documentary footage, realistic movement, available light",
        "fantasy": "fantasy atmosphere, imaginative details, dramatic lighting",
    }
    orientation = "wide landscape composition, 16:9" if job["aspect_ratio"] == "16:9" else "vertical portrait composition, 9:16"
    prompt = f"{job['prompt']}. {style_words.get(job['style'], style_words['cinematic'])}. {orientation}. No captions, no subtitles, no text overlay."
    frames = {4: 33, 5: 41, 6: 49, 8: 65}[int(job["duration"])]
    client = InferenceClient(provider=HF_PROVIDER, api_key=HF_TOKEN, timeout=600)
    video_bytes = client.text_to_video(prompt, model=HF_MODEL, num_frames=frames)
    if not isinstance(video_bytes, (bytes, bytearray)) or len(video_bytes) < 1024:
        raise RuntimeError("The hosted model did not return a usable video file. Try again later.")
    (OUTPUT / filename).write_bytes(video_bytes)
    return filename

def run_job(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return
        job["status"] = "processing"
        job["started_at"] = now()
    save_jobs()
    try:
        # Keep only one hosted generation running at a time to avoid accidental duplicate requests.
        with active_generation_lock:
            with jobs_lock:
                current = jobs[job_id]
                current["status"] = "processing"
            filename = make_video_with_hosted_model(job)
        with jobs_lock:
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["video_url"] = f"/videos/{filename}"
            jobs[job_id]["download_url"] = f"/downloads/{filename}"
            jobs[job_id]["completed_at"] = now()
            jobs[job_id]["note"] = "Generated by Magic Hour LTX-2.5 at 480p for 5 seconds." if MAGIC_HOUR_API_KEY else "Generated by a hosted Hugging Face AI text-to-video model. Output and duration depend on provider/model limits."
    except Exception as exc:
        message = str(exc)
        for secret in (HF_TOKEN, MAGIC_HOUR_API_KEY):
            if secret:
                message = message.replace(secret, "[hidden token]")
        # Do not silently substitute a fake text-card video if hosted inference fails.
        with jobs_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = ("Hosted AI generation failed. This can happen when free credits are exhausted, the model/provider is unavailable, or your token lacks inference permission. No demo text-card was substituted. Details: " + message)[:700]
    save_jobs()

@app.get("/")
def home():
    return send_from_directory(STATIC, "index.html")

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "product": "Phenesty AI Video Studio", "generator": "hosted-text-to-video", "configured": bool(MAGIC_HOUR_API_KEY or HF_TOKEN), "provider": "magic-hour" if MAGIC_HOUR_API_KEY else HF_PROVIDER, "model": "ltx-2.5 (480p, 5 seconds)" if MAGIC_HOUR_API_KEY else HF_MODEL})

@app.get("/api/jobs")
def list_jobs():
    with jobs_lock:
        result = sorted(jobs.values(), key=lambda x: x.get("created_at", ""), reverse=True)[:20]
    return jsonify(result)

@app.post("/api/generate")
def generate():
    body = request.get_json(silent=True) or {}
    prompt = re.sub(r"\s+", " ", str(body.get("prompt", ""))).strip()
    if len(prompt) < 5:
        return jsonify({"error": "Please enter a prompt of at least 5 characters."}), 400
    if len(prompt) > 500:
        return jsonify({"error": "Please keep prompts under 500 characters."}), 400
    duration = body.get("duration", 5)
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        duration = 5
    if duration not in (5,):
        return jsonify({"error": "The current free-tier Magic Hour model supports 5-second clips. Please select 5 seconds."}), 400
    aspect = body.get("aspect_ratio", "16:9")
    if aspect not in ("16:9", "9:16"):
        return jsonify({"error": "Choose 16:9 or 9:16 aspect ratio."}), 400
    style = str(body.get("style", "cinematic"))
    if style not in ("cinematic", "animation", "documentary", "fantasy"):
        style = "cinematic"
    if not (MAGIC_HOUR_API_KEY or HF_TOKEN):
        return jsonify({"error": "No video provider is configured. Add MAGIC_HOUR_API_KEY in Render Environment to use Magic Hour trial credits. No demo video will be generated."}), 503
    job_id = uuid.uuid4().hex[:12]
    job = {"id": job_id, "prompt": prompt, "duration": duration, "aspect_ratio": aspect, "style": style, "status": "queued", "created_at": now()}
    with jobs_lock:
        jobs[job_id] = job
    save_jobs()
    threading.Thread(target=run_job, args=(job_id,), daemon=True).start()
    return jsonify(job), 202

@app.get("/api/jobs/<job_id>")
def get_job(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"error": "Job not found."}), 404
        return jsonify(job)

@app.get("/videos/<path:filename>")
def get_video(filename):
    if not re.fullmatch(r"[a-f0-9]{12}\.mp4", filename):
        abort(404)
    return send_from_directory(OUTPUT, filename, as_attachment=False, mimetype="video/mp4")

@app.get("/downloads/<path:filename>")
def download_video(filename):
    if not re.fullmatch(r"[a-f0-9]{12}\.mp4", filename):
        abort(404)
    return send_from_directory(OUTPUT, filename, as_attachment=True, download_name=f"phenesty-ai-{filename}", mimetype="video/mp4")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
