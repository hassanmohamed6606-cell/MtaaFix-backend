
import os
import base64
from io import BytesIO
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv()

cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
api_key = os.getenv("CLOUDINARY_API_KEY")
api_secret = os.getenv("CLOUDINARY_API_SECRET")

if not all([cloud_name, api_key, api_secret]):
    raise ValueError("Missing Cloudinary credentials in .env")

cloudinary.config(
    cloud_name=cloud_name,
    api_key=api_key,
    api_secret=api_secret,
    secure=True
)

# Generate a tiny valid PNG image for testing
png_data = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j4l8AAAAASUVORK5CYII="
)

try:
    print("Connecting to Cloudinary...")
    
    result = cloudinary.uploader.upload(
        BytesIO(png_data),
        folder="mtaafix/reports",
        resource_type="image",
        public_id="mtaafix_connection_test",
        overwrite=True
    )

    print("\nSUCCESS: Image uploaded!")
    print("Public ID:", result.get("public_id"))
    print("Secure URL:", result.get("secure_url"))

except Exception as error:
    print("\nCLOUDINARY ERROR:")
    print(error)
