import io
import socket
from flask import Flask, render_template, request, send_file, jsonify
from PIL import Image, ImageFilter

app = Flask(__name__)

# Render the image processing upload page
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# Process image using requested operation and return PNG with container ID header
@app.route('/process', methods=['POST'])
def process():
    file = request.files.get('image')
    operation = request.form.get('operation')

    # Basic input validation
    if not file or file.filename == '':
        return 'Missing image file', 400
    if operation not in ['grayscale', 'blur', 'rotate']:
        return 'Invalid operation', 400

    # Open image and apply the selected transformation
    img = Image.open(file.stream)
    if operation == 'grayscale':
        img = img.convert('L')
    elif operation == 'blur':
        img = img.filter(ImageFilter.BLUR)
    elif operation == 'rotate':
        img = img.rotate(90, expand=True)

    # Export processed image to memory buffer as PNG
    out = io.BytesIO()
    img.save(out, format='PNG')
    out.seek(0)

    # Return image with container hostname header
    response = send_file(out, mimetype='image/png')
    response.headers['X-Container-ID'] = socket.gethostname()
    return response

# Return service health and container hostname
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'container_id': socket.gethostname()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
