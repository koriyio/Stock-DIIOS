from flask import Flask
app = Flask(__name__, static_folder='.', static_url_path='')
@app.route('/<path:filename>')
def serve_html(filename): return ''
print('Success')
