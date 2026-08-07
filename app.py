from flask import Flask, request, render_template_string, send_file, jsonify
import yt_dlp
import os
import uuid
import re
import logging
from datetime import datetime

# ================================================================
# LOGGING SETUP - To see exact errors
# ================================================================
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Downloads folder
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# ================================================================
# HTML TEMPLATE (Frontend)
# ================================================================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎓 Edu Downloader - Render</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.97);
            border-radius: 24px;
            padding: 40px 35px;
            max-width: 600px;
            width: 100%;
            box-shadow: 0 30px 80px rgba(0, 0, 0, 0.6);
        }
        .header { text-align: center; margin-bottom: 25px; }
        .header .icon { font-size: 48px; display: block; }
        .header h1 {
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(135deg, #ff0000, #cc0000);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .header p { color: #666; font-size: 14px; margin-top: 4px; }
        .header p span {
            background: #ffeeee;
            padding: 2px 12px;
            border-radius: 20px;
            color: #cc0000;
            font-weight: 600;
            font-size: 12px;
        }
        .input-group { display: flex; gap: 10px; margin-bottom: 15px; }
        .input-group input {
            flex: 1;
            padding: 14px 18px;
            border: 2px solid #e0e0e0;
            border-radius: 14px;
            font-size: 15px;
            font-family: inherit;
            outline: none;
            transition: 0.3s;
            background: #f8f9fa;
        }
        .input-group input:focus {
            border-color: #ff0000;
            background: #fff;
            box-shadow: 0 0 0 4px rgba(255, 0, 0, 0.08);
        }
        .input-group button {
            padding: 14px 30px;
            background: #ff0000;
            color: white;
            border: none;
            border-radius: 14px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            transition: 0.3s;
            font-family: inherit;
            white-space: nowrap;
        }
        .input-group button:hover {
            background: #cc0000;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(255, 0, 0, 0.3);
        }
        .input-group button:disabled {
            background: #999;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .quality-section {
            display: flex;
            gap: 8px;
            margin-bottom: 18px;
            flex-wrap: wrap;
            justify-content: center;
        }
        .quality-section label {
            background: #f0f2f5;
            padding: 8px 18px;
            border-radius: 30px;
            cursor: pointer;
            transition: 0.3s;
            font-size: 13px;
            font-weight: 600;
            color: #333;
            border: 2px solid transparent;
        }
        .quality-section label:hover { background: #e0e0e0; }
        .quality-section input[type="radio"] { display: none; }
        .quality-section input[type="radio"]:checked+label {
            background: #ff0000;
            color: white;
            border-color: #ff0000;
            box-shadow: 0 4px 15px rgba(255, 0, 0, 0.25);
        }
        #status {
            text-align: center;
            padding: 12px 16px;
            border-radius: 12px;
            display: none;
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 12px;
        }
        #status.loading { display: block; background: #fff3cd; color: #856404; }
        #status.success { display: block; background: #d4edda; color: #155724; }
        #status.error { display: block; background: #f8d7da; color: #721c24; }
        #status.info { display: block; background: #d1ecf1; color: #0c5460; }
        #videoInfo {
            display: none;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 16px;
            margin-top: 15px;
            text-align: center;
            border: 1px solid #e9ecef;
        }
        #videoInfo img {
            max-width: 100%;
            border-radius: 12px;
            max-height: 180px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        #videoInfo .title { margin-top: 12px; font-weight: 700; font-size: 16px; color: #1a1a1a; }
        #videoInfo .meta { font-size: 13px; color: #666; margin: 6px 0 14px 0; }
        .download-link {
            display: inline-block;
            padding: 14px 40px;
            background: #28a745;
            color: white;
            border-radius: 14px;
            text-decoration: none;
            font-weight: 700;
            transition: 0.3s;
            font-size: 16px;
        }
        .download-link:hover {
            background: #218838;
            transform: scale(1.03);
            box-shadow: 0 8px 25px rgba(40, 167, 69, 0.3);
        }
        .info-box {
            background: #f8f9fa;
            padding: 14px 18px;
            border-radius: 14px;
            margin-top: 18px;
            font-size: 12px;
            color: #555;
            border-left: 4px solid #ff0000;
            line-height: 1.7;
        }
        .info-box strong { color: #cc0000; }
        .footer { text-align: center; margin-top: 18px; font-size: 12px; color: #aaa; }
        .footer a { color: #ff0000; text-decoration: none; font-weight: 600; }
        #progressBar {
            width: 100%;
            height: 5px;
            background: #e9ecef;
            border-radius: 4px;
            margin: 12px 0;
            overflow: hidden;
            display: none;
        }
        #progressBar .fill {
            height: 100%;
            background: linear-gradient(90deg, #ff0000, #cc0000);
            width: 0%;
            border-radius: 4px;
            transition: width 0.5s;
        }
        @media (max-width: 480px) {
            .container { padding: 20px 15px; }
            .input-group { flex-direction: column; }
            .input-group button { width: 100%; justify-content: center; }
            .header h1 { font-size: 22px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="icon">🎓</span>
            <h1>Edu Downloader</h1>
            <p>📥 <span>Education Purpose Only</span> • Hosted on Render</p>
        </div>

        <div class="input-group">
            <input type="text" id="urlInput" placeholder="Paste YouTube URL here..." value="https://youtu.be/">
            <button id="downloadBtn">⬇ Download</button>
        </div>

        <div class="quality-section">
            <input type="radio" name="quality" id="q1080" value="1080">
            <label for="q1080">1080p</label>
            <input type="radio" name="quality" id="q720" value="720" checked>
            <label for="q720">720p</label>
            <input type="radio" name="quality" id="q480" value="480">
            <label for="q480">480p</label>
            <input type="radio" name="quality" id="q360" value="360">
            <label for="q360">360p</label>
            <input type="radio" name="quality" id="qaudio" value="audio">
            <label for="qaudio">🎵 Audio</label>
        </div>

        <div id="progressBar"><div class="fill" id="progressFill"></div></div>
        <div id="status"></div>
        <div id="videoInfo"></div>

        <div class="info-box">
            <strong>📌 How to use:</strong><br>
            1️⃣ Paste YouTube video URL (lectures, tutorials, etc.)<br>
            2️⃣ Select quality<br>
            3️⃣ Click Download — file will save automatically<br>
            <span style="color:#999;font-size:11px;">⚠️ For educational use only • Videos are not stored on server</span>
        </div>

        <div class="footer">
            Made with ❤️ for Students &nbsp;|&nbsp; <a href="#" onclick="resetAll();return false;">🔄 Reset</a>
        </div>
    </div>

    <script>
        const urlInput = document.getElementById('urlInput');
        const downloadBtn = document.getElementById('downloadBtn');
        const statusDiv = document.getElementById('status');
        const videoInfoDiv = document.getElementById('videoInfo');
        const progressFill = document.getElementById('progressFill');
        const progressBar = document.getElementById('progressBar');

        function getQuality() {
            const selected = document.querySelector('input[name="quality"]:checked');
            return selected ? selected.value : '720';
        }

        function setStatus(msg, type = 'loading') {
            statusDiv.textContent = msg;
            statusDiv.className = type;
            statusDiv.style.display = 'block';
        }

        function hideStatus() {
            statusDiv.className = '';
            statusDiv.style.display = 'none';
        }

        function setProgress(percent) {
            progressBar.style.display = 'block';
            progressFill.style.width = percent + '%';
        }

        function hideProgress() {
            progressBar.style.display = 'none';
            progressFill.style.width = '0%';
        }

        function resetAll() {
            hideStatus();
            hideProgress();
            videoInfoDiv.style.display = 'none';
            videoInfoDiv.innerHTML = '';
            downloadBtn.disabled = false;
            downloadBtn.textContent = '⬇ Download';
            urlInput.value = 'https://youtu.be/';
            urlInput.focus();
        }

        function isValidUrl(url) {
            const patterns = [
                /(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/,
                /youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})/,
                /youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/
            ];
            return patterns.some(p => p.test(url));
        }

        async function downloadVideo() {
            const url = urlInput.value.trim();

            if (!url) {
                setStatus('❌ Please paste a YouTube URL first!', 'error');
                return;
            }

            if (!isValidUrl(url)) {
                setStatus('❌ Invalid YouTube URL! Please check and try again.', 'error');
                return;
            }

            const quality = getQuality();

            downloadBtn.disabled = true;
            downloadBtn.textContent = '⏳ Processing...';
            videoInfoDiv.style.display = 'none';
            hideProgress();
            setStatus('🔄 Downloading... Please wait.', 'loading');
            setProgress(20);

            try {
                const formData = new FormData();
                formData.append('url', url);
                formData.append('quality', quality);

                const response = await fetch('/download', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    let errorMsg = 'Download failed';
                    try {
                        const errorData = await response.json();
                        errorMsg = errorData.error || errorMsg;
                    } catch (e) {}
                    throw new Error(errorMsg);
                }

                setProgress(80);

                // Get the file
                const blob = await response.blob();
                const contentDisposition = response.headers.get('content-disposition');
                let filename = 'video.mp4';
                if (contentDisposition) {
                    const match = contentDisposition.match(/filename="(.+)"/);
                    if (match) filename = match[1];
                }

                setProgress(100);

                // Create download link
                const downloadUrl = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(downloadUrl);

                setStatus('✅ Download complete! File saved successfully.', 'success');

                setTimeout(() => {
                    hideProgress();
                }, 3000);

            } catch (error) {
                console.error('Error:', error);
                setStatus(`❌ ${error.message || 'Something went wrong. Please try again.'}`, 'error');
            }

            downloadBtn.disabled = false;
            downloadBtn.textContent = '⬇ Download';
        }

        downloadBtn.addEventListener('click', downloadVideo);

        urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') downloadVideo();
        });

        window.addEventListener('load', () => {
            setStatus('🌐 Ready! Paste URL and click Download.', 'info');
            setTimeout(hideStatus, 3000);
        });
    </script>
</body>
</html>
'''

# ================================================================
# FIX: Regular expression with raw string
# ================================================================
URL_REGEX = re.compile(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})')

# ================================================================
# FLASK ROUTES - yt-dlp + Cookies
# ================================================================

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download():
    try:
        url = request.form.get('url')
        quality = request.form.get('quality', '720')
        
        logger.info(f"Download request received: URL={url}, Quality={quality}")
        
        if not url:
            return jsonify({'error': 'URL nahi daala!'}), 400
        
        # Validate URL
        match = URL_REGEX.search(url)
        if not match:
            logger.error(f"Invalid URL: {url}")
            return jsonify({'error': 'Invalid YouTube URL!'}), 400
        
        video_id = match.group(1)
        logger.info(f"Video ID extracted: {video_id}")
        
        # ============================================================
        #  COOKIE FILE PATH - Render Secret File
        # ============================================================
        cookie_file_path = os.environ.get('YOUTUBE_COOKIE_FILE_PATH', '/etc/secrets/cookies.txt')
        logger.info(f"Looking for cookie file at: {cookie_file_path}")
        
        # Check if cookie file exists
        if not os.path.exists(cookie_file_path):
            logger.error(f"Cookie file not found at: {cookie_file_path}")
            return jsonify({'error': f'Cookie file not found at {cookie_file_path}! Please upload cookies.txt as Secret File on Render.'}), 500
        
        logger.info(f"Cookie file found at: {cookie_file_path}")
        
        # Unique ID for each download
        download_id = str(uuid.uuid4())[:8]
        output_path = os.path.join(DOWNLOAD_FOLDER, download_id)
        os.makedirs(output_path, exist_ok=True)
        logger.info(f"Output path created: {output_path}")
        
        # Quality mapping
        quality_map = {
            '1080': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            '720': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            '480': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
            '360': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
            'audio': 'bestaudio/best'
        }
        
        format_spec = quality_map.get(quality, 'bestvideo[height<=720]+bestaudio/best[height<=720]')
        logger.info(f"Format spec: {format_spec}")
        
        # ============================================================
        #  yt-dlp OPTIONS with COOKIES + ANTI-BOT SETTINGS
        # ============================================================
        if quality == 'audio':
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'cookiefile': cookie_file_path,
                'quiet': False,  # Set to False for debugging
                'no_warnings': False,
                'no_check_certificate': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                        'player_skip': ['webpage'],
                    }
                }
            }
        else:
            ydl_opts = {
                'format': format_spec,
                'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'cookiefile': cookie_file_path,
                'quiet': False,  # Set to False for debugging
                'no_warnings': False,
                'no_check_certificate': True,
                'extract_flat': False,
                'ignoreerrors': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                        'player_skip': ['webpage'],
                    }
                }
            }
        
        # Download with yt-dlp
        logger.info("Starting yt-dlp download...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video').replace('/', '_').replace('\\', '_')
            logger.info(f"Downloaded video: {title}")
            
            # Find downloaded file
            files = os.listdir(output_path)
            if not files:
                logger.error("No files found in output directory")
                return jsonify({'error': 'File download nahi hui'}), 500
            
            filename = files[0]
            file_path = os.path.join(output_path, filename)
            logger.info(f"Sending file: {file_path}")
            
            # Determine mimetype
            mimetype = 'audio/mpeg' if quality == 'audio' else 'video/mp4'
            ext = 'mp3' if quality == 'audio' else 'mp4'
            
            # Send file
            return send_file(
                file_path,
                as_attachment=True,
                download_name=f"{title}.{ext}",
                mimetype=mimetype
            )
            
    except Exception as e:
        logger.error(f"Download error: {str(e)}", exc_info=True)
        error_msg = str(e)
        if 'Sign in to confirm' in error_msg or 'bot' in error_msg.lower():
            error_msg = 'YouTube bot detection! Cookies might be expired. Please refresh cookies.txt and redeploy.'
        elif 'HTTP Error 403' in error_msg:
            error_msg = 'YouTube ne block kar diya! Cookies refresh karein.'
        return jsonify({'error': error_msg}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
    
