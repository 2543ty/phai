const form = document.querySelector("#generate-form");
const promptInput = document.querySelector("#prompt");
const charCount = document.querySelector("#char-count");
const generateBtn = document.querySelector("#generate-btn");
const statusText = document.querySelector("#status-text");
const statusIcon = document.querySelector(".status-icon");
const previewContent = document.querySelector("#preview-content");
const resultVideo = document.querySelector("#result-video");
const downloadLink = document.querySelector("#download-link");
const outputSize = document.querySelector("#output-size");
const previewCanvas = document.querySelector("#preview-canvas");
let activeJob = null;
let pollTimer = null;

promptInput.addEventListener("input", () => {
  charCount.textContent = `${promptInput.value.length} / 500`;
});
document.querySelectorAll(".example").forEach(button => {
  button.addEventListener("click", () => {
    promptInput.value = button.dataset.prompt;
    promptInput.dispatchEvent(new Event("input"));
    promptInput.focus();
  });
});
document.querySelectorAll('input[name="ratio"]').forEach(input => {
  input.addEventListener("change", () => {
    document.querySelectorAll(".ratio").forEach(label => label.classList.remove("selected"));
    input.closest(".ratio").classList.add("selected");
  });
});

function setStatus(message, icon = "✦") {
  statusText.textContent = message;
  statusIcon.textContent = icon;
}
function setBusy(busy) {
  generateBtn.disabled = busy;
  generateBtn.innerHTML = busy
    ? '<span class="spinner"></span> Generating real AI video…'
    : '<span>✦</span> Generate AI video <span class="arrow">↗</span>';
}
function resetVideo() {
  resultVideo.pause();
  resultVideo.removeAttribute("src");
  resultVideo.hidden = true;
  previewContent.hidden = false;
  downloadLink.classList.add("disabled");
  downloadLink.setAttribute("aria-disabled", "true");
  downloadLink.removeAttribute("href");
}
async function pollJob(jobId) {
  try {
    const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
    const job = await response.json();
    if (!response.ok) throw new Error(job.error || "Could not check job status.");
    if (job.status === "completed") {
      clearInterval(pollTimer);
      setBusy(false);
      previewContent.hidden = true;
      resultVideo.hidden = false;
      resultVideo.src = job.video_url;
      resultVideo.load();
      downloadLink.href = job.download_url || job.video_url;
      downloadLink.classList.remove("disabled");
      downloadLink.setAttribute("aria-disabled", "false");
      downloadLink.setAttribute("download", `phenesty-ai-${job.id}.mp4`);
      outputSize.textContent = `${job.duration}s · ${job.aspect_ratio} · MP4`;
      activeJob = false;
      setStatus("Your AI-generated video is ready", "✓");
      return;
    }
    if (job.status === "failed") { activeJob = false; throw new Error(job.error || "Video generation failed."); }
    setStatus(job.status === "queued" ? "Queued for cloud AI generation…" : "The hosted AI model is generating your scene…", "◌");
  } catch (error) {
    clearInterval(pollTimer);
    setBusy(false);
    activeJob = false;
    setStatus(error.message, "!");
  }
}
form.addEventListener("submit", async event => {
  event.preventDefault();
  if (activeJob) return;
  const prompt = promptInput.value.trim();
  if (prompt.length < 5) {
    setStatus("Please write a more detailed prompt.", "!");
    return;
  }
  clearInterval(pollTimer);
  resetVideo();
  setBusy(true);
  activeJob = true;
  outputSize.textContent = "Generating…";
  setStatus("Sending your prompt…", "◌");
  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        prompt,
        style: document.querySelector("#style").value,
        duration: Number(document.querySelector("#duration").value),
        aspect_ratio: document.querySelector('input[name="ratio"]:checked').value
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not start generation.");
    setStatus("Request sent to the hosted AI model…", "◌");
    activeJob = false;
    pollTimer = setInterval(() => pollJob(data.id), 900);
    await pollJob(data.id);
  } catch (error) {
    activeJob = false;
    setBusy(false);
    outputSize.textContent = "No output yet";
    activeJob = false;
    setStatus(error.message, "!");
  }
});
