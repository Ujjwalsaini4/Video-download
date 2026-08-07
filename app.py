from flask import Flask, request, render_template, send_file, jsonify, after_this_request
import yt_dlp
import os
import uuid
import re
import shutil
import json
import logging
import traceback
from datetime import datetime
from urllib.parse import urlparse

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TEMP_FOLDER = '/tmp/downloads'
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Cookies file path - multiple fallback options
COOKIES_PATHS = [
    os.environ.get('COOKIES_FILE_PATH', ''),
    '/etc/secrets/cookies.txt',  # Render Secret Files
    '/tmp/cookies.txt',
    './cookies.txt',
    os.path.join(os.path.dirname(__file__), 'cookies.txt')
]

def get_cookies_file():
    """Find valid cookies file from multiple paths"""
    for path in COOKIES_PATHS:
        if path and os.path.exists(path) and os.path.getsize(path) > 0:
            logger.info(f"✅ Cookies found at: {path}")
            return path
    
    # Try to get cookies from environment variable (JSON format)
    cookies_json = os.environ.get('YOUTUBE_COOKIES_JSON')
    if cookies_json:
        try:
            temp_cookie_file = os.path.join(TEMP_FOLDER, f'cookies_{uuid.uuid4().hex}.txt')
            with open(temp_cookie_file, 'w') as f:
                f.write(cookies_json)
            logger.info(f"✅ Cookies created from env var: {temp_cookie_file}")
            return temp_cookie_file
        except Exception as e:
            logger.error(f"Failed to create cookies from env: {e}")
    
    logger.warning("⚠️ No cookies file found - may get bot errors")
    return None

def get_ydl_opts(format_id=None, is_audio=False):
    """Generate yt-dlp options with cookies support"""
    
    cookies_file = get_cookies_file()
    
    opts = {
        'quiet': True,
        'no_warnings': False,
        'ignoreerrors': True,
        'no_color': True,
        'extract_flat': False,
        'verbose': False,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }
    
    # Add cookies if available
    if cookies_file:
        opts['cookiefile'] = cookies_file
        logger.info(f"🍪 Using cookies: {cookies_file}")
    
    # Add format-specific options
    if is_audio:
        opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(TEMP_FOLDER, f'{uuid.uuid4().hex}_%(title)s.%(ext)s'),
        })
    else:
        opts.update({
            'format': format_id or 'best[height<=1080]',
            'outtmpl': os.path.join(TEMP_FOLDER, f'{uuid.uuid4().hex}_%(title)s.%(ext)s'),
        })
    
    return opts

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def get_video_info(url):
    """Get video information without downloading"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': False,
        'ignoreerrors': True,
        'extract_flat': False,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'cookiefile': get_cookies_file() if get_cookies_file() else None,
    }
    
    try:
        logger.info(f"Fetching info for URL: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                logger.error("No info returned")
                return None
            
            # Get available formats
            formats = []
            seen_formats = set()
            
            for f in info.get('formats', []):
                format_key = f"{f.get('height', 'audio')}_{f.get('ext', '')}"
                if format_key in seen_formats:
                    continue
                seen_formats.add(format_key)
                
                height = f.get('height')
                if height:
                    resolution = f"{height}p"
                    if f.get('fps') and f.get('fps') > 30:
                        resolution += f" {f.get('fps')}fps"
                else:
                    resolution = 'audio only'
                
                format_info = {
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext', 'unknown'),
                    'resolution': resolution,
                    'filesize': f.get('filesize') or f.get('filesize_approx'),
                    'acodec': f.get('acodec', 'none'),
                    'vcodec': f.get('vcodec', 'none'),
                    'note': f.get('format_note', ''),
                    'fps': f.get('fps'),
                }
                formats.append(format_info)
            
            # Sort formats: video quality high to low, then audio
            formats.sort(key=lambda x: (
                0 if x['resolution'] != 'audio only' else 1,
                -int(x['resolution'].replace('p', '').replace(' audio only', '')) if x['resolution'] != 'audio only' and x['resolution'].replace('p', '').replace(' audio only', '').isdigit() else 0
            ))
            
            # Limit formats to avoid UI clutter
            formats = formats[:15]
            
            result = {
                'title': info.get('title', 'Untitled'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'views': info.get('view_count', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'uploader_url': info.get('uploader_url', ''),
                'description': info.get('description', '')[:200],
                'formats': formats,
                'success': True
            }
            
            logger.info(f"✅ Successfully fetched info: {result['title']}")
            return result
            
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"DownloadError: {str(e)}")
        if 'Sign in to confirm' in str(e):
            return {'error': 'Bot detection triggered. Please add valid cookies.'}
        return {'error': f'Download error: {str(e)}'}
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}\n{traceback.format_exc()}")
        return {'error': f'Error: {str(e)}'}

def download_video(url, format_id=None, is_audio=False):
    """Download video or audio"""
    try:
        opts = get_ydl_opts(format_id, is_audio)
        logger.info(f"Downloading: {url} (audio: {is_audio})")
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Find the downloaded file
            base_filename = opts['outtmpl']
            pattern = base_filename.replace('%(title)s', '*').replace('%(ext)s', '*')
            import glob
            downloaded_files = glob.glob(pattern)
            
            if downloaded_files:
                return downloaded_files[0]
            
            # Try alternative method
            filename = ydl.prepare_filename(info)
            if os.path.exists(filename):
                return filename
            
            # If audio, try with mp3 extension
            if is_audio:
                audio_filename = filename.rsplit('.', 1)[0] + '.mp3'
                if os.path.exists(audio_filename):
                    return audio_filename
            
            logger.error(f"File not found: {filename}")
            return None
            
    except Exception as e:
        logger.error(f"Download error: {str(e)}\n{traceback.format_exc()}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'cookies_available': bool(get_cookies_file())
    })

@app.route('/get_info', methods=['POST'])
def get_info():
    """Get video information"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Validate YouTube URL
        if not any(domain in url.lower() for domain in ['youtube.com', 'youtu.be']):
            return jsonify({'error': 'Please enter a valid YouTube URL'}), 400
        
        info = get_video_info(url)
        
        if not info:
            return jsonify({'error': 'Failed to fetch video info'}), 400
        
        if 'error' in info:
            return jsonify({'error': info['error']}), 400
        
        return jsonify(info)
        
    except Exception as e:
        logger.error(f"Error in get_info: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download():
    """Download video"""
    try:
        url = request.form.get('url', '').strip()
        format_id = request.form.get('format_id', 'best')
        is_audio = request.form.get('audio', 'false') == 'true'
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Validate YouTube URL
        if not any(domain in url.lower() for domain in ['youtube.com', 'youtu.be']):
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        file_path = download_video(url, format_id, is_audio)
        
        if not file_path or not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return jsonify({'error': 'Download failed - file not created'}), 500
        
        # Get filename for download
        filename = os.path.basename(file_path)
        # Clean up temporary folder name
        filename = re.sub(r'^[a-f0-9]{32}_', '', filename)
        
        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up: {file_path}")
                # Clean up temp folder if empty
                dir_path = os.path.dirname(file_path)
                if os.path.exists(dir_path) and not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except Exception as e:
                logger.error(f"Cleanup error: {str(e)}")
            return response
        
        return send_file(
            file_path, 
            as_attachment=True, 
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/download_audio', methods=['POST'])
def download_audio():
    """Download audio only"""
    try:
        url = request.form.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not any(domain in url.lower() for domain in ['youtube.com', 'youtu.be']):
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        file_path = download_video(url, is_audio=True)
        
        if not file_path or not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            return jsonify({'error': 'Audio download failed'}), 500
        
        filename = os.path.basename(file_path)
        filename = re.sub(r'^[a-f0-9]{32}_', '', filename)
        if not filename.endswith('.mp3'):
            filename = filename.rsplit('.', 1)[0] + '.mp3'
        
        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up audio: {file_path}")
                dir_path = os.path.dirname(file_path)
                if os.path.exists(dir_path) and not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except Exception as e:
                logger.error(f"Cleanup error: {str(e)}")
            return response
        
        return send_file(
            file_path, 
            as_attachment=True, 
            download_name=filename,
            mimetype='audio/mpeg'
        )
        
    except Exception as e:
        logger.error(f"Audio download error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Audio download failed: {str(e)}'}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
