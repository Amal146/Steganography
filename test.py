from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

# Helper functions for encryption and decryption
def encrypt_password(password):
    with open("public.pem", "rb") as file:
        public_key = RSA.import_key(file.read())
    cipher = PKCS1_OAEP.new(public_key)
    encrypted_password = cipher.encrypt(password.encode())
    return encrypted_password

def decrypt_password(encrypted_password):
    with open("private.pem", "rb") as file:
        private_key = RSA.import_key(file.read())
    cipher = PKCS1_OAEP.new(private_key)
    decrypted_password = cipher.decrypt(encrypted_password)
    return decrypted_password.decode()


password = "secretpassword"
encrypted = encrypt_password(password)
print("Encrypted:", encrypted)
decrypted = decrypt_password(encrypted)
print("Decrypted:", decrypted)
