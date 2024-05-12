from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import pyaes, pbkdf2, binascii, os, secrets
from fastapi.staticfiles import StaticFiles
from stegano import lsb
from typing import Optional
import numpy as np  
from PIL import Image  
from base64 import b64decode
from sqlalchemy.orm import Session
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES 
from Crypto.Util.Padding import pad, unpad
from database import SessionLocal, engine
from models import User
import models, schemas
from database import Base, engine, SessionLocal
import schemas
import os 
import tempfile
import hashlib

app = FastAPI()

db = SessionLocal()

Base.metadata.create_all(engine)

app.mount("/static", StaticFiles(directory="static"), name="static")

# File paths for RSA keys
PUBLIC_KEY_PATH = "public.pem"
PRIVATE_KEY_PATH = "private.pem"

# Generate RSA key pair if the keys do not exist
if not (os.path.exists(PUBLIC_KEY_PATH) and os.path.exists(PRIVATE_KEY_PATH)):
    key = RSA.generate(2048)
    private_key = key.export_key()
    public_key = key.publickey().export_key()

    # Save public key to a file (for encryption during signup)
    with open(PUBLIC_KEY_PATH, "wb") as file:
        file.write(public_key)

    # Save private key to a file (for decryption during login)
    with open(PRIVATE_KEY_PATH, "wb") as file:
        file.write(private_key)

# Helper functions for encryption and decryption
def encrypt_password(password):
    with open(PUBLIC_KEY_PATH, "rb") as file:
        public_key = RSA.import_key(file.read())
    cipher = PKCS1_OAEP.new(public_key)
    encrypted_password = cipher.encrypt(password.encode())
    return encrypted_password

def decrypt_password(encrypted_password):
    with open(PRIVATE_KEY_PATH, "rb") as file:
        private_key = RSA.import_key(file.read())
    cipher = PKCS1_OAEP.new(private_key)
    decrypted_password = cipher.decrypt(encrypted_password)
    return decrypted_password.decode()

 

# Signup endpoint
@app.post("/signup/")
async def signup(username: str = Form(...), password: str = Form(...)):
    # Check if the username already exists
    existing_user = db.query(models.User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Encrypt the password
    encrypted_password = encrypt_password(password)

    # Create new user record
    new_user = User(username=username, password=encrypted_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User signed up successfully"}

# Login endpoint
@app.post("/login/")
async def login(username: str = Form(...), password: str = Form(...)):
    existing_user = db.query(models.User).filter(User.username == username).first()
    if existing_user:
        decrypted_password = decrypt_password(existing_user.password)
        if decrypted_password  == password:  # Compare decrypted password with plaintext password
            return {"message": "User login successful"}
        else:
            raise HTTPException(status_code=400, detail="Invalid password" + "decrypted_password" + decrypted_password)
    else:
        raise HTTPException(status_code=401, detail="Invalid username" + "decrypted_password" + decrypted_password)


#Encrypt_message_using _simple_substitution_cipher
def encrypt_message(message, key):
    encrypted_message = ""
    key_index = 0
    for char in message:
        # Perform XOR operation between the character and the corresponding character in the key
        encrypted_char = chr(ord(char) ^ ord(key[key_index % len(key)]))
        encrypted_message += encrypted_char
        key_index = (key_index + 1) % len(key)
    encrypted_message += "//ECRP%"
    return encrypted_message



def decrypt_message(encrypted_message, key):
    decrypted_message = ""
    key_index = 0
    for char in encrypted_message:
        # Perform XOR operation between the character of the encrypted message and the corresponding character in the key
        decrypted_char = chr(ord(char) ^ ord(key[key_index % len(key)]))
        decrypted_message += decrypted_char
        key_index = (key_index + 1) % len(key)
    return decrypted_message


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
async def encode_image(algo: str = Form(...), file: UploadFile = File(...), message: str = Form(...), key: Optional[str] = Form(None)):
    
    contents = await file.read()
    with open(file.filename, "wb") as f:
        f.write(contents)
    # Handle encryption if key is provided
    if key:
        message = encrypt_message(message, key)
    
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
async def decode_image(file: UploadFile = File(...),key: Optional[str] = Form(None)):

    # Save the contents of the uploaded file to a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    try:
        # Decode the message
        decoded_message = decode_lsb(temp_file_path)

        if decoded_message.endswith("//ECRP%"):
            if key:
                decoded_message = decoded_message.replace("//ECRP%", "")
                decoded_message = decrypt_message(decoded_message, key)


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
async def embed_message(algo: str = Form(...), file: UploadFile = File(...), message: str = Form(...), key: Optional[str] = Form(None)):
    # Open the uploaded image
    img = Image.open(file.file)
    if key:
        message = encrypt_message(message, key)

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



