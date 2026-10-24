const form=document.querySelector("#generate-form");
const promptInput=document.querySelector("#prompt");
const count=document.querySelector("#char-count");
const button=document.querySelector("#generate-btn");
const statusText=document.querySelector("#status-text");
const video=document.querySelector("#result-video");
const download=document.querySelector("#download-link");
let busy=false,timer=null;
promptInput.addEventListener("input",()=>count.textContent=promptInput.value.length+" / 500");
function status(s){statusText.textContent=s}
async function check(id){
 try{
  const r=await fetch("/api/jobs/"+encodeURIComponent(id));const job=await r.json();
  if(!r.ok)throw Error(job.error||"Could not check generation status.");
  if(job.status==="completed"){
   clearInterval(timer);busy=false;button.disabled=false;status("Your AI-generated video is ready.");
   video.src=job.video_url;video.hidden=false;download.href=job.download_url||job.video_url;download.hidden=false;return;
  }
  if(job.status==="failed")throw Error(job.error||"Generation failed.");
  status(job.status==="queued"?"Queued for hosted AI generation…":"The AI model is generating your video…");
 }catch(e){clearInterval(timer);busy=false;button.disabled=false;status(e.message)}
}
form.addEventListener("submit",async e=>{
 e.preventDefault();if(busy)return;
 busy=true;button.disabled=true;video.hidden=true;video.removeAttribute("src");download.hidden=true;status("Sending prompt to hosted AI…");
 try{
  const r=await fetch("/api/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt:promptInput.value.trim(),style:document.querySelector("#style").value,duration:Number(document.querySelector("#duration").value),aspect_ratio:document.querySelector("#ratio").value})});
  const data=await r.json();if(!r.ok)throw Error(data.error||"Could not start generation.");
  timer=setInterval(()=>check(data.id),1500);await check(data.id);
 }catch(e){busy=false;button.disabled=false;status(e.message)}
});
