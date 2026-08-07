from flask import Flask, request, render_template, send_file, jsonify, after_this_request
import yt_dlp
import os
import uuid
import re
import shutil
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# Temporary folder for downloads
TEMP_FOLDER = '/tmp/downloads'
os.makedirs(TEMP_FOLDER, exist_ok=True)

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def get_video_info(url):
    """Get video information without downloading"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get available formats
            formats = []
            for f in info.get('formats', []):
                if f.get('height') or f.get('acodec') != 'none':
                    format_info = {
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'resolution': f'{f.get("height", "audio")}p' if f.get('height') else 'audio',
                        'filesize': f.get('filesize'),
                        'acodec': f.get('acodec'),
                        'vcodec': f.get('vcodec'),
                        'note': f.get('format_note', '')
                    }
                    formats.append(format_info)
            
            return {
                'title': info.get('title', 'Untitled'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'views': info.get('view_count', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'formats': formats[:10]  # Limit to first 10 formats
            }
    except Exception as e:
        print(f"Error getting video info: {str(e)}")
        return None

def download_video(url, format_id=None, is_audio=False):
    """Download video or audio"""
    unique_id = str(uuid.uuid4())
    output_path = os.path.join(TEMP_FOLDER, unique_id)
    os.makedirs(output_path, exist_ok=True)
    
    if is_audio:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
    else:
        ydl_opts = {
            'format': format_id or 'best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # If audio, the file might have different extension
            if is_audio and not os.path.exists(filename):
                # Try with .mp3 extension
                base = os.path.splitext(filename)[0]
                filename = base + '.mp3'
            
            return filename
    except Exception as e:
        print(f"Download error: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_info', methods=['POST'])
def get_info():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    info = get_video_info(url)
    if not info:
        return jsonify({'error': 'Failed to fetch video info'}), 400
    
    return jsonify(info)

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    format_id = request.form.get('format_id')
    is_audio = request.form.get('audio') == 'true'
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    file_path = download_video(url, format_id, is_audio)
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Download failed'}), 500
    
    @after_this_request
    def cleanup(response):
        try:
            # Delete the file after sending
            os.remove(file_path)
            # Remove the directory if empty
            dir_path = os.path.dirname(file_path)
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
        except Exception as e:
            print(f"Cleanup error: {str(e)}")
        return response
    
    return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))

@app.route('/download_audio', methods=['POST'])
def download_audio():
    url = request.form.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    file_path = download_video(url, is_audio=True)
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Download failed'}), 500
    
    @after_this_request
    def cleanup(response):
        try:
            os.remove(file_path)
            dir_path = os.path.dirname(file_path)
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
        except Exception as e:
            print(f"Cleanup error: {str(e)}")
        return response
    
    return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
