function fetchInfo() {
    const url = document.getElementById('urlInput').value.trim();
    const errorDiv = document.getElementById('errorMsg');
    const loader = document.getElementById('loader');
    const infoDiv = document.getElementById('videoInfo');

    errorDiv.textContent = '';
    infoDiv.style.display = 'none';

    if (!url) {
        errorDiv.textContent = '❌ Please enter a YouTube URL';
        return;
    }

    // Validate YouTube URL
    const youtubeRegex = /(youtube\.com|youtu\.be)/;
    if (!youtubeRegex.test(url)) {
        errorDiv.textContent = '❌ Please enter a valid YouTube URL';
        return;
    }

    loader.style.display = 'block';

    fetch('/get_info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
    })
    .then(res => res.json())
    .then(data => {
        loader.style.display = 'none';

        if (data.error) {
            errorDiv.textContent = '❌ ' + data.error;
            return;
        }

        // Display video info
        document.getElementById('thumbnail').src = data.thumbnail || '';
        document.getElementById('videoTitle').textContent = data.title || 'Untitled';
        document.getElementById('videoUploader').textContent = '👤 ' + (data.uploader || 'Unknown');
        document.getElementById('videoViews').textContent = '👁️ ' + formatNumber(data.views || 0) + ' views';

        // Populate formats
        const select = document.getElementById('formatSelect');
        select.innerHTML = '';
        const formats = data.formats || [];

        if (formats.length === 0) {
            const opt = document.createElement('option');
            opt.value = 'best';
            opt.textContent = 'Best Quality';
            select.appendChild(opt);
        } else {
            formats.forEach(f => {
                const opt = document.createElement('option');
                opt.value = f.format_id;
                const size = f.filesize ? ' (' + formatFileSize(f.filesize) + ')' : '';
                const res = f.resolution || 'audio';
                opt.textContent = res + ' - ' + f.ext + size;
                select.appendChild(opt);
            });
        }

        infoDiv.style.display = 'block';
        infoDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    })
    .catch(err => {
        loader.style.display = 'none';
        errorDiv.textContent = '❌ Network error: ' + err.message;
        console.error(err);
    });
}

function downloadVideo() {
    const url = document.getElementById('urlInput').value.trim();
    const formatId = document.getElementById('formatSelect').value;
    const progressBar = document.getElementById('progressBar');
    const progressFill = document.getElementById('progressFill');

    if (!url) {
        document.getElementById('errorMsg').textContent = '❌ Please enter a URL first';
        return;
    }

    // Show progress (simulated)
    progressBar.style.display = 'block';
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 10;
        if (progress > 100) progress = 100;
        progressFill.style.width = progress + '%';
        if (progress >= 100) {
            clearInterval(interval);
            setTimeout(() => {
                progressBar.style.display = 'none';
                progressFill.style.width = '0%';
            }, 1000);
        }
    }, 300);

    // Create form and submit
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/download';

    const urlInput = document.createElement('input');
    urlInput.type = 'hidden';
    urlInput.name = 'url';
    urlInput.value = url;
    form.appendChild(urlInput);

    const formatInput = document.createElement('input');
    formatInput.type = 'hidden';
    formatInput.name = 'format_id';
    formatInput.value = formatId || 'best';
    form.appendChild(formatInput);

    const audioInput = document.createElement('input');
    audioInput.type = 'hidden';
    audioInput.name = 'audio';
    audioInput.value = 'false';
    form.appendChild(audioInput);

    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
}

function downloadAudio() {
    const url = document.getElementById('urlInput').value.trim();
    const progressBar = document.getElementById('progressBar');
    const progressFill = document.getElementById('progressFill');

    if (!url) {
        document.getElementById('errorMsg').textContent = '❌ Please enter a URL first';
        return;
    }

    // Show progress (simulated)
    progressBar.style.display = 'block';
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 10;
        if (progress > 100) progress = 100;
        progressFill.style.width = progress + '%';
        if (progress >= 100) {
            clearInterval(interval);
            setTimeout(() => {
                progressBar.style.display = 'none';
                progressFill.style.width = '0%';
            }, 1000);
        }
    }, 300);

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/download_audio';

    const urlInput = document.createElement('input');
    urlInput.type = 'hidden';
    urlInput.name = 'url';
    urlInput.value = url;
    form.appendChild(urlInput);

    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatFileSize(bytes) {
    if (bytes === 0 || !bytes) return 'Unknown';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + sizes[i];
}

// Enter key support
document.getElementById('urlInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') fetchInfo();
});
