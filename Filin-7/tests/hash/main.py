import hashlib

password = b'11111111'
hashed_password = hashlib.sha256(password).hexdigest()
print((hashed_password))