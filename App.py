yt-dlp Flask Downloader - Modern UI + Live Progress (ASCII safe)

Single-file app. Run:  python app.py

Requirements: pip install flask yt-dlp

Needs ffmpeg on PATH (Termux: pkg install ffmpeg)

from flask import Flask, request, render_template_string, send_file, abort, jsonify import tempfile, shutil, os, glob, io, threading, uuid, math

---- Optional: hardcode ffmpeg folder if not on PATH ----

FFMPEG_PATH = os.environ.get('FFMPEG_PATH', '')  # e.g. r"C:\Users\YourName\ffmpeg\bin" if FFMPEG_PATH and os.path.isdir(FFMPEG_PATH): os.environ['PATH'] = FFMPEG_PATH + os.pathsep + os.environ.get('PATH', '')

---- SSL check (yt-dlp needs it) ----

try: import ssl  # noqa except ModuleNotFoundError: raise RuntimeError("Python is missing SSL support. Install from python.org.")

from yt_dlp import YoutubeDL

app = Flask(name)

---------------------- UI ----------------------

HTML = r''' <!doctype html>

<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>YouTube Video Downloader</title>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root{--bg:#eaf6ff;--card:#ffffff;--txt:#0f172a;--muted:#6b7280;--accent:#2563eb;--accent2:#22c55e;--ring:#93c5fd}
    *{box-sizing:border-box}
    body{margin:0;background:linear-gradient(180deg,#eaf6ff, #e8f0ff);font-family:'Poppins',system-ui, -apple-system, Segoe UI, Arial;color:var(--txt)}
    .wrap{max-width:980px;margin:42px auto;padding:24px}
    .hero{background:var(--card);border-radius:20px;padding:28px 24px 24px;box-shadow:0 10px 35px rgba(37,99,235,.15);position:relative;overflow:hidden}
    .hero:before{content:"";position:absolute;inset:-60px -80px auto auto;width:280px;height:280px;background:radial-gradient(120px 120px at 70% 30%, var(--ring), transparent 60%);opacity:.35;transform:rotate(18deg)}
    h1{font-size:34px;letter-spacing:.3px;margin:2px 0 8px}
    p.sub{margin:0 0 18px;color:var(--muted)}
    label{font-weight:600;font-size:14px;margin:14px 4px 8px;display:block}
    input,select,button{width:100%;padding:12px 14px;border-radius:14px;border:1px solid #e5e7eb;background:#f8fafc;font-size:15px;outline:none}
    input:focus,select:focus{border-color:var(--ring);box-shadow:0 0 0 4px rgba(147,197,253,.35)}
    .row{display:grid;grid-template-columns:1fr 240px 180px;gap:12px}
    .btn{background:var(--accent);color:#fff;border:none;font-weight:600;cursor:pointer;transition:transform .04s ease, box-shadow .2s}
    .btn:hover{transform:translateY(-1px)}
    .btn:active{transform:translateY(0)}
    .muted{font-size:12px;color:var(--muted);margin-top:10px}
    .bar{height:12px;background:#eef2ff;border-radius:999px;overflow:hidden;margin-top:14px;box-shadow:inset 0 0 0 1px #e5e7eb}
    .bar>span{display:block;height:100%;width:0%;background:linear-gradient(90deg,var(--accent),var(--accent2));transition:width .25s}
    .stats{display:flex;gap:14px;margin-top:10px;color:#475569;font-size:13px}
    .chip{background:#f1f5f9;border:1px solid #e2e8f0;padding:6px 10px;border-radius:999px}
    .ok{color:#16a34a}
    .err{color:#dc2626}
    .hidden{display:none}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>YouTube Video Downloader</h1>
      <p class="sub">Download videos with audio (MP4) or audio-only (MP3). Progress shown live. <strong>Use for content you have rights to.</strong></p><label>Video URL</label>
  <input id="url" placeholder="https://www.youtube.com/watch?v=..." required>

  <div class="row">
    <div>
      <label>Format</label>
      <select id="format">
        <option value="mp4_4k">4K MP4 (video+audio)</option>
        <option value="mp4_1080">1080p MP4 (video+audio)</option>
        <option value="mp4_720" selected>720p MP4 (video+audio)</option>
        <option value="mp4_best">Best MP4 (video+audio)</option>
        <option value="audio_mp3">Audio Only (MP3)</option>
      </select>
    </div>
    <div>
      <label>Filename (optional)</label>
      <input id="fname" placeholder="my-video">
    </div>
    <div style="align-self:end">
      <button id="go" class="btn">Search & Download</button>
    </div>
  </div>

  <div id="progressWrap" class="hidden">
    <div class="bar"><span id="bar"></span></div>
    <div class="stats">
      <span class="chip" id="pct">0%</span>
      <span class="chip" id="spd">–</span>
      <span class="chip" id="eta">ETA –</span>
      <span class="chip ok hidden" id="done">Ready • downloading file…</span>
      <span class="chip err hidden" id="fail">Failed</span>
    </div>
  </div>

  <p class="muted">Tip: If audio is missing, install <code>ffmpeg</code> and restart the app. Windows users can set PATH to the <code>bin</code> folder.</p>
</div>

  </div>  <script>
    const $ = (q)=>document.querySelector(q);
    const go = $('#go');
    const bar = $('#bar');
    const pct = $('#pct');
    const spd = $('#spd');
    const eta = $('#eta');
    const done = $('#done');
    const fail = $('#fail');
    const wrap = $('#progressWrap');

    let pollTimer = null, jobId = null;

    function updateUI(p){
      wrap.classList.remove('hidden');
      const percent = Math.max(0, Math.min(100, Math.round(p.percent || 0)));
      bar.style.width = percent + '%';
      pct.textContent = percent + '%';
      spd.textContent = p.speed || '–';
      eta.textContent = 'ETA ' + (p.eta || '–');
      if(p.status === 'finished'){
        done.classList.remove('hidden');
      }
      if(p.status === 'error'){
        fail.classList.remove('hidden');
      }
    }

    async function start(){
      fail.classList.add('hidden');
      done.classList.add('hidden');
      bar.style.width = '0%';
      const body = {
        url: $('#url').value.trim(),
        format_choice: $('#format').value,
        filename: $('#fname').value.trim()
      };
      if(!body.url){ alert('Please paste a URL'); return; }

      const res = await fetch('/start', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
      if(!res.ok){ fail.classList.remove('hidden'); return; }
      const j = await res.json();
      jobId = j.job_id;
      poll();
    }

    async function poll(){
      clearTimeout(pollTimer);
      const res = await fetch('/progress/' + jobId);
      if(!res.ok){ fail.classList.remove('hidden'); return; }
      const p = await res.json();
      updateUI(p);
      if(p.status === 'finished'){
        // trigger download
        window.location = '/fetch/' + jobId;
        return;
      }
      if(p.status === 'error') return;
      pollTimer = setTimeout(poll, 800);
    }

    go.addEventListener('click', start);
  </script></body>
</html>
'''---------------- Download back-end with progress ----------------

JOBS = {}

class Job: def init(self): self.id = str(uuid.uuid4()) self.tmpdir = tempfile.mkdtemp(prefix='ydl_') self.status = 'queued'  # queued, downloading, finished, error self.percent = 0.0 self.speed = '' self.eta = '' self.out_path = None self.err = '' JOBS[self.id] = self

def cleanup(self):
    shutil.rmtree(self.tmpdir, ignore_errors=True)

def _human_rate(n): try: n = float(n) except Exception: return '-' units = ['B/s','KB/s','MB/s','GB/s'] i = 0 while n >= 1024 and i < len(units)-1: n /= 1024.0 i += 1 return f"{n:.1f} {units[i]}"

def run_download(job: Job, url: str, choice: str, custom_name: str | None): try: fmt_map = { 'mp4_4k': 'bestvideo[height<=4320]+bestaudio/best', 'mp4_1080': 'bestvideo[height<=1080]+bestaudio/best', 'mp4_720': 'bestvideo[height<=720]+bestaudio/best', 'mp4_best': 'bestvideo+bestaudio/best', 'audio_mp3': 'bestaudio/best' } fmt = fmt_map.get(choice, 'bestvideo+bestaudio/best')

outtmpl = os.path.join(job.tmpdir, (custom_name if custom_name else '%(title)s') + '.%(ext)s')

    def hook(d):
        if d.get('status') == 'downloading':
            job.status = 'downloading'
            tot = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            done = d.get('downloaded_bytes', 0)
            job.percent = (done / tot * 100) if tot else 0.0
            sp = d.get('speed')
            job.speed = _human_rate(sp) if sp else '-'
            eta = d.get('eta')
            job.eta = f"{eta}s" if eta else '-'
        elif d.get('status') == 'finished':
            # Download completed; wait for merge/post-processing to finish
            job.status = 'processing'
            job.percent = 100.0
            job.speed = '-'
            job.eta = 'merging…'

    ydl_opts = {
        'format': fmt,
        'outtmpl': outtmpl,
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'progress_hooks': [hook],
        'postprocessor_hooks': [hook],
        'quiet': True,
    }
    # audio-only → mp3
    if choice == 'audio_mp3':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'
        }]
    # point yt-dlp to ffmpeg if explicitly set
    if FFMPEG_PATH:
        ydl_opts['ffmpeg_location'] = FFMPEG_PATH

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    # pick largest output file
    files = glob.glob(os.path.join(job.tmpdir, '*'))
    if not files:
        raise RuntimeError('Download finished but file not found')
    files.sort(key=lambda p: os.path.getsize(p), reverse=True)
    job.out_path = files[0]
    job.status = 'finished'
except Exception as e:
    job.status = 'error'
    job.err = str(e)

@app.post('/start') def start_job(): data = request.get_json(force=True) url = data.get('url', '').strip() choice = data.get('format_choice', 'mp4_720') custom = (data.get('filename') or '').strip()

if not url:
    abort(400, 'URL required')

job = Job()
t = threading.Thread(target=run_download, args=(job, url, choice, custom or None), daemon=True)
t.start()
return jsonify({'job_id': job.id})

@app.get('/progress/<jid>') def progress(jid): job = JOBS.get(jid) if not job: abort(404) return jsonify({ 'status': job.status, 'percent': job.percent, 'speed': job.speed, 'eta': job.eta, 'error': job.err })

@app.get('/fetch/<jid>') def fetch(jid): job = JOBS.get(jid) if not job: abort(404) if job.status != 'finished' or not job.out_path: abort(400, 'Not ready') # read into memory for simplicity with open(job.out_path, 'rb') as f: data = f.read() bio = io.BytesIO(data) bio.seek(0) fname = os.path.basename(job.out_path) # cleanup job after serving job.cleanup() return send_file(bio, as_attachment=True, download_name=fname)

@app.get('/') def index(): return render_template_string(HTML)

if name == 'main': # Option 3 default is 720p (as requested) app.run(debug=True)
