import os
import io
import pandas as pd
import requests
from flask import Flask, request, send_file, jsonify, send_from_directory

# Initialize Flask app
app = Flask(__name__)

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'xlsx', 'csv'}

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_url(url):
    """
    Checks if a URL exists and returns its existence status and redirected URL.

    Args:
        url (str): The URL to check.

    Returns:
        tuple: (is_exist: bool, redirected_url: str)
               is_exist is True if the URL is accessible (status code < 400), False otherwise.
               redirected_url is the final URL after redirects, or "NA" if no redirect or URL doesn't exist.
    """
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        # Handle non-string or invalid URL formats gracefully
        return False, "NA (Invalid URL format)"

    try:
        response = requests.get(url, allow_redirects=True, timeout=10)
        is_exist = response.status_code < 400
        redirected_url = "NA"

        if is_exist:
            # Check if redirection occurred
            if response.history:
                redirected_url = response.url
            # else: keep redirected_url as "NA"
        # else: keep redirected_url as "NA"

        return is_exist, redirected_url

    except requests.exceptions.RequestException as e:
        # Handle connection errors, timeouts, etc.
        # print(f"Error checking URL {url}: {e}") # Optional: log the error
        return False, f"NA (Error: {type(e).__name__})"
    except Exception as e:
        # Handle other potential errors during request
        # print(f"Unexpected error checking URL {url}: {e}") # Optional: log the error
        return False, f"NA (Unexpected Error: {type(e).__name__})"


# Serve index.html from the parent directory
@app.route('/')
def serve_index():
    # Construct the absolute path to the parent directory relative to this script
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return send_from_directory(parent_dir, 'index.html')

# Route for favicon.ico to avoid 404 errors
@app.route('/favicon.ico')
def favicon():
    # Return "No Content" response
    return '', 204


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handles file upload, processes URLs, and returns the processed file.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = file.filename
        file_ext = filename.rsplit('.', 1)[1].lower()

        try:
            # Read the file into a pandas DataFrame
            if file_ext == 'xlsx':
                # Use BytesIO to read the file stream directly without saving
                file_stream = io.BytesIO(file.read())
                df = pd.read_excel(file_stream, engine='openpyxl')
                file_stream.seek(0) # Reset stream position if needed later
            elif file_ext == 'csv':
                 # Use BytesIO to read the file stream directly
                file_stream = io.BytesIO(file.read())
                # Try detecting encoding, default to utf-8
                try:
                    df = pd.read_csv(file_stream)
                except UnicodeDecodeError:
                    file_stream.seek(0) # Reset stream position
                    df = pd.read_csv(file_stream, encoding='latin1') # Try latin1 as fallback
                file_stream.seek(0) # Reset stream position

            # Case-insensitive check for "Urls" column
            url_col = None
            for col in df.columns:
                if col.lower() == 'urls':
                    url_col = col
                    break

            if url_col is None:
                return jsonify({"error": "Column 'Urls' not found in the file"}), 400

            # Apply the URL checking function
            results = df[url_col].apply(check_url)
            df['is_exist'] = results.apply(lambda x: x[0])
            df['redirected'] = results.apply(lambda x: x[1])

            # Prepare the output file in memory
            output_buffer = io.BytesIO()
            output_filename = f"processed_{filename}"

            if file_ext == 'xlsx':
                df.to_excel(output_buffer, index=False, engine='openpyxl')
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif file_ext == 'csv':
                df.to_csv(output_buffer, index=False, encoding='utf-8')
                mimetype = 'text/csv'

            output_buffer.seek(0)

            # Send the processed file back to the user
            return send_file(
                output_buffer,
                as_attachment=True,
                download_name=output_filename,
                mimetype=mimetype
            )

        except pd.errors.EmptyDataError:
             return jsonify({"error": "Uploaded file is empty"}), 400
        except Exception as e:
            # Catch potential errors during file reading or processing
            # print(f"Error processing file: {e}") # Optional: log the error
            return jsonify({"error": f"An error occurred processing the file: {str(e)}"}), 500

    else:
        return jsonify({"error": "Invalid file type. Only .xlsx and .csv allowed"}), 400

# Run the Flask development server
if __name__ == '__main__':
    # Make sure the app runs on 0.0.0.0 to be accessible externally if needed
    # Use a specific port if desired, default is 5000
    app.run(host='0.0.0.0', port=10290, debug=True)