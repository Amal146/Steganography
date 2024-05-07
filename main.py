from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from stegano import lsb
import numpy as np  
from PIL import Image  
import os
import tempfile


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


#encode function using LSB endpoint

def encode_lsb(carrier_image_path, message):
    # Open the carrier image
    img = Image.open(carrier_image_path)
    
    # Encode the message into the image
    encoded_image = lsb.hide(img, message)
    
    # Get the directory of the carrier image
    directory = os.path.dirname(carrier_image_path)
    # Get the filename of the carrier image without extension
    filename = os.path.splitext(os.path.basename(carrier_image_path))[0]
    # Construct the path for the encoded image
    encoded_image_path = os.path.join(directory, f"encoded_{filename}.png")
    
    # Save the encoded image
    encoded_image.save(encoded_image_path)
    return encoded_image_path


#encode endpoint using LSB endpoint
@app.post("/encode/")
async def encode_image(algo: str = Form(...), file: UploadFile = File(...), message: str = Form(...)):
    
    contents = await file.read()
    with open(file.filename, "wb") as f:
        f.write(contents)
    encoded_image_path = encode_lsb(file.filename, message)
    return FileResponse(encoded_image_path, media_type="image/png")



#decode function using LSB endpoint

def decode_lsb(encoded_image_path):
    try:
        # Extract the message
        decoded_message = lsb.reveal(encoded_image_path)
        return decoded_message
    except (IOError, ValueError) as e:
        # Handle potential errors like file not found or invalid image format
        print(f"Error: {e}")
        return None


#decode endpoint using LSB endpoint
@app.post("/decode/")
async def decode_image(file: UploadFile = File(...)):

    # Save the contents of the uploaded file to a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    try:
        # Decode the message
        decoded_message = decode_lsb(temp_file_path)

        if decoded_message:
            html_content = f"""
            <script>
                // Show an alert with the decoded message
                alert("Decoded Message: {decoded_message}");
            </script>
            """
        else:
            html_content = """
            <script>
                // Show an alert if no message is found
                alert("No message found in the stego-image.");
            </script>
            """
    except Exception as e:
        print(f"Error: {e}")
        html_content = """
        <script>
            // Show an alert if an error occurs during decoding
            alert("Impossible to detect message. Please check inputs");
        </script>
        """
    
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

    return HTMLResponse(content=html_content)



def embed_message_in_bpc(original_image, secret_message):
    # Convert the original image to a NumPy array
    original_image_array = np.array(original_image)

    # Convert the secret message to a binary string
    binary_message = ''.join(format(ord(char), '08b') for char in secret_message)

    # Get image dimensions and message length
    image_height, image_width, _ = original_image_array.shape
    message_length = len(binary_message)

    # Check if there's enough space in the image for the message
    if message_length > image_height * image_width * 0.5:
        raise ValueError("Insufficient space in image to embed message.")

    # Split the message into bits and convert them to integers
    message_bits = [int(bit) for bit in binary_message]

    # Flatten the image into a 1D array for easier processing
    flat_image = original_image_array.flatten()

    # Embed the secret message one bit at a time using BPCS
    for i in range(message_length):
        # Get the LSB (Least Significant Bit) of the current pixel
        lsb = flat_image[i] & 1

        # Modify the LSB to match the secret message bit
        if message_bits[i] == 0 and lsb == 1:
            flat_image[i] -= 1
        elif message_bits[i] == 1 and lsb == 0:
            flat_image[i] += 1

    # Reshape the modified image data back to its original form
    stego_image = flat_image.reshape(original_image_array.shape)

    return stego_image


@app.post("/embed_message/")
async def embed_message(algo: str = Form(...), file: UploadFile = File(...), message: str = Form(...)):
    # Open the uploaded image
    img = Image.open(file.file)

    # Embed the message in the image using BPC
    stego_image = embed_message_in_bpc(img, message)

    # Save the stego image temporarily
    temp_stego_image_path = "temp_stego_image.png"
    stego_image_pil = Image.fromarray(stego_image)
    stego_image_pil.save(temp_stego_image_path)

    # Return the path to the temporary stego image
    return temp_stego_image_path


@app.get("/welcome", response_class=HTMLResponse)
async def upload_image_form():
    with open("welcome.html", "r") as file:
        return HTMLResponse(file.read())

@app.get("/explore.html", response_class=HTMLResponse)
async def upload_image_form():
    with open("explore.html", "r") as file:
        return HTMLResponse(file.read())
    
@app.get("/needs.html", response_class=HTMLResponse)
async def upload_image_form():
    with open("needs.html", "r") as file:
        return HTMLResponse(file.read())
    
@app.get("/encryp.html", response_class=HTMLResponse)
async def upload_image_form():
    with open("encryp.html", "r") as file:
        return HTMLResponse(file.read())

@app.get("/yet.html", response_class=HTMLResponse)
async def upload_image_form():
    with open("yet.html", "r") as file:
        return HTMLResponse(file.read())
    
@app.get("/decryp.html", response_class=HTMLResponse)
async def upload_image_form():
    with open("decryp.html", "r") as file:
        return HTMLResponse(file.read())

@app.get("/", response_class=HTMLResponse)
async def upload_image_form():
    with open("login.html", "r") as file:
        return HTMLResponse(file.read())
    
@app.get("/signup.html", response_class=HTMLResponse)
async def upload_image_form():
    with open("signup.html", "r") as file:
        return HTMLResponse(file.read())

@app.get("/style.css")
async def get_style_css():
    with open("static\style.css", "r") as file:
        return file.read()



