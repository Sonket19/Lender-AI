import base64
from google import genai
from google.genai.types import GenerateContentConfig
from config.settings import settings
import asyncio

# Initialize Google Gen AI client
client = genai.Client(
    vertexai=True,
    project=settings.GCP_PROJECT_ID,
    location=settings.GCP_LOCATION
)

async def generate_deal_cover_art(deal_id: str, company_name: str, sector: str, description: str) -> str:
    """
    Generate a professional cover art image for a deal using Gemini Image Generation.
    Returns the base64 encoded image string.
    """
    print(f"[{deal_id}] 🎨 Generating cover art for {company_name} ({sector})...")
    
    prompt = f"""
    Create a professional, abstract, high-quality background image for a startup dashboard.
    
    Startup Name: {company_name}
    Sector: {sector}
    Description: {description}
    
    Style: Modern, sleek, digital art, abstract, suitable for a business dashboard header. 
    The image should be wide (landscape aspect ratio).
    Avoid text in the image.
    Use colors that represent the sector (e.g., blue/green for fintech, green for agritech, dark/neon for cyber).
    Make it look premium and futuristic.
    """
    
    try:
        # Generate image using Imagen 3 via Gemini API
        # Note: The exact method call might vary depending on the library version.
        # Using the standard generate_images method for Imagen.
        
        response = client.models.generate_images(
            model='imagen-3.0-generate-001',
            prompt=prompt,
            config=genai.types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
                include_rai_reason=True,
                output_mime_type="image/jpeg"
            )
        )
        
        if response.generated_images:
            image = response.generated_images[0]
            # The image bytes are in image.image.image_bytes
            image_bytes = image.image.image_bytes
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            print(f"[{deal_id}] ✅ Cover art generated successfully!")
            return f"data:image/jpeg;base64,{base64_image}"
        else:
            print(f"[{deal_id}] ⚠️ No image generated.")
            return None
            
    except Exception as e:
        print(f"[{deal_id}] ❌ Error generating cover art: {str(e)}")
        # Return None so the frontend uses the default gradient
        return None

        return None
