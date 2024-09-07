from flask import Flask, render_template, request, flash, redirect, url_for, send_file
import yt_dlp as YoutubeDL
import ast
import re

app = Flask(__name__)
app.secret_key = 'supersecretkey'

YOUTUBE_REGEX = re.compile(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

@app.template_filter('filesizeformat')
def filesizeformat(value):
    if isinstance(value, (int, float)):
        value = float(value)
        if value < 1024:
            return f"{value} B"
        elif value < 1024 ** 2:
            return f"{value / 1024:.2f} KB"
        elif value < 1024 ** 3:
            return f"{value / (1024 ** 2):.2f} MB"
        else:
            return f"{value / (1024 ** 3):.2f} GB"
    else:
        return "Unknown Size"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/formats', methods=['POST'])
def formats():
    url = request.form['url']

    if not re.match(YOUTUBE_REGEX, url):
        flash("Error: Please provide a valid YouTube URL.", "danger")
        return redirect(url_for('index'))

    ydl_opts = {}

    try:
        with YoutubeDL.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            info = ydl.sanitize_info(info_dict)
            thumbnail_url = info.get('thumbnail', '')
            video_title = info.get('fulltitle', 'Video: Unknown Title')
            web_page_url = info.get('webpage_url', '').split('v=')[-1]
            video_formats = [f for f in info.get('formats', []) if f['vcodec'] != 'none' and f['acodec'] == 'none' and f['ext'] == 'mp4']
            audio_formats = next(f for f in info.get('formats', []) if f.get('vcodec', "") == 'none' and f.get('acodec', 'none') != 'none' and f['ext'] == 'm4a')
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('index'))

    return render_template('formats.html', 
        formats=video_formats, 
        url=web_page_url, 
        thumbnail_url=thumbnail_url, 
        video_title=video_title,
        audio_formats=audio_formats
    )

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    best_video_data = request.form.get('format_id', "")
    best_audio_data = request.form.get('audio_formats', "")
    best_video = ast.literal_eval(best_video_data)
    best_audio = ast.literal_eval(best_audio_data)

    if not best_video and not best_audio:
        flash("Error: No format selected. Please select a format and try again.", "danger")
        return redirect(url_for('formats', url=url))
    
    def repe(ctx):
        yield {
            'format_id': f'{best_video["format_id"]}+{best_audio["format_id"]}',
            'ext': best_video['ext'],
            'requested_formats': [best_video, best_audio],
            'protocol': f'{best_video["protocol"]}+{best_audio["protocol"]}'
        }

    ydl_opts = {
        'format': repe,
        'outtmpl': '%(title)s.%(ext)s',
    }

    try:
        with YoutubeDL.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_title = ydl.prepare_filename(info_dict)
            ydl.download([url])
        return send_file(video_title, as_attachment=True)

    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)