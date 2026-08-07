let currentVideoInfo = null;

function showError(message) {
    const errorDiv = document.getElementById('errorMsg');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 8000);
}

function hideError() {
    document.getElementById('errorMsg').style.display = 'none';
}

function showLoader(show) {
    document.getElementById('loader').style.display = show ? 'block' : 'none';
}

function showVideoInfo(show) {
    document.getElementById('videoInfo').style.display = show ? 'block' : 'none';
}

function formatNumber(num) {
    if (!num) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatDuration(seconds) {
    if (!seconds) return '0:00';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function formatFileSize(bytes) {
    if (!bytes) return 'Unknown';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + sizes[i];
}

function fetchInfo() {
    const url = document.getElementById('urlInput').value.trim();
    hideError();
    showVideoInfo(false);

    if (!url) {
        showError('❌ Please enter a YouTube URL');
        return;
    }

    // Validate YouTube URL
    const youtubeRegex = /(youtube\.com|youtu\.be)/;
    if (!youtubeRegex.test(url)) {
        showError('❌ Please enter a valid YouTube URL');
        return;
    }

    showLoader(true);
    document.getElementById('fetchBtn').disabled = true;

    fetch('/get_info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
    })
    .then(res => res.json())
    .then(data => {
        showLoader(false);
        document.getElementById('fetchBtn').disabled = false;

        if (data.error) {
            showError('❌ ' + data.error);
            return;
        }

        currentVideoInfo = data;

        // Display video info
        document.getElementById('thumbnail').src = data.thumbnail || '';
        document.getElementById('thumbnail').alt = data.title || 'Video thumbnail';
        document.getElementById('videoTitle').textContent = data.title || 'Untitled';
        document.getElementById('videoUploader').textContent = '👤 ' + (data.uploader || 'Unknown');
        document.getElementById('videoViews').textContent = '👁️ ' + formatNumber(data.views) + ' views';
        document.getElementById('videoDuration').textContent = '⏱️ ' + formatDuration(data.duration);

        // Populate formats
        const select = document.getElementById('formatSelect');
        select.innerHTML = '';
        
        // Add best quality option
        const bestOpt = document.createElement('option');
        bestOpt.value = 'best';
        bestOpt.textContent = '⭐ Best Quality (Auto)';
        select.appendChild(bestOpt);

        // Add format options
        const formats = data.formats || [];
        let hasFormats = false;
        
        formats.forEach(f => {
            if (f.resolution === 'audio only') {
                const opt = document.createElement('option');
                opt.value = f.format_id;
                const size = f.filesize ? ' (' + formatFileSize(f.filesize) + ')' : '';
                opt.textContent = '🎵 Audio - ' + f.ext + size;
                select.appendChild(opt);
                hasFormats = true;
            } else {
                const opt = document.createElement('option');
                opt.value = f.format_id;
                const size = f.filesize ? ' (' + formatFileSize(f.filesize) + ')' : '';
                const note = f.note ? ' ' + f.note : '';
                opt.textContent = f.resolution + ' - ' + f.ext + size + note;
                select.appendChild(opt);
                hasFormats = true;
            }
        });

        if (!hasFormats) {
            const opt = document.createElement('option');
            opt.value = 'best';
            opt.textContent = 'Default Quality';
            select.appendChild(opt);
        }

        showVideoInfo(true);
        document.getElementById('videoInfo').scrollIntoView({ behavior: 'smooth', block: 'start' });
    })
    .catch(err => {
        showLoader(false);
        document.getElementById('fetchBtn').disabled = false;
        showError('❌ Network error: ' + err.message);
        console.error('Fetch error:', err);
    });
}

function showProgress(message) {
    const progressBar = document.getElementById('progressBar');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    progressBar.style.display = 'block';
    progressText.textContent = message || 'Preparing download...';
    progressFill.style.width = '0%';
}

function updateProgress(percent, message) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    progressFill.style.width = Math.min(percent, 100) + '%';
    if (message) {
        progressText.textContent = message;
    }
}

function hideProgress() {
    const progressBar = document.getElementById('progressBar');
    setTimeout(() => {
        progressBar.style.display = 'none';
        document.getElementById('progressFill').style.width = '0%';
    }, 1000);
}

function downloadVideo() {
    const url = document.getElementById('urlInput').value.trim();
    const formatId = document.getElementById('formatSelect').value;

    if (!url) {
        showError('❌ Please enter a URL first');
        return;
    }

    showProgress('Starting video download...');
    updateProgress(10, 'Preparing video...');

    // Create and submit form
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/download';

    const urlInput = document.createElement('input');
    urlInput.type = 'hidden';
