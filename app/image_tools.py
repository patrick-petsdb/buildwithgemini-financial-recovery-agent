"""Image generation tool for Financial Scam Recovery Agent.

Uses gemini-3.1-flash-lite-image in the global Vertex AI region.
Saves the generated image as an ADK artifact (Playground Artifacts panel)
and uploads it to the public Google Cloud Storage bucket.
"""

import time
import uuid
from typing import Any
from google import genai
from google.adk.tools.tool_context import ToolContext
from google.cloud import storage
from google.genai import types
from google.genai.types import GenerateContentConfig, Modality

PROJECT_ID = "qwiklabs-gcp-03-44680d3a8b6a"
BUCKET_NAME = "financial-recovery-assets-qwiklabs-gcp-03-44680d3a8b6a"


async def generate_recovery_roadmap_image(
    prompt: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Generate a visual recovery roadmap or milestone infographic for a scam recovery case.

    Generates the visual using gemini-3.1-flash-lite-image, saves it to the ADK session
    artifacts panel, uploads the bytes to the public Cloud Storage bucket, and returns
    the public HTTPS image URL.

    Args:
        prompt: Detailed description of the infographic or roadmap visual to generate
                (e.g., 'A calm, modern, and structured visual recovery timeline card for
                imposter bank scam recovery showing 4 milestones: Emergency Freeze,
                Dispute Filing, Police Report, and Account Restabilization.').
        tool_context: ADK ToolContext injected by the runtime for saving artifacts.

    Returns:
        A dictionary containing the public HTTPS URL of the image, the artifact filename,
        and display guidance.
    """
    try:
        # 1. Initialize GenAI client configured for Vertex AI in global location
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

        enhanced_prompt = (
            f"{prompt}. High quality, clean modern infographic card, calm and reassuring aesthetic, "
            "clear graphical milestones, professional layout."
        )

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=enhanced_prompt,
            config=GenerateContentConfig(
                response_modalities=[Modality.IMAGE],
            ),
        )

        img_bytes = None
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    img_bytes = part.inline_data.data
                    break

        if not img_bytes:
            return {
                "status": "error",
                "message": "Model did not return image data in the response.",
            }

        filename = f"recovery_roadmap_{int(time.time())}_{uuid.uuid4().hex[:6]}.png"

        # 2. Save image as an ADK session artifact for Playground panel
        artifact_part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")
        artifact_version = None
        try:
            artifact_version = await tool_context.save_artifact(
                filename=filename, artifact=artifact_part
            )
        except Exception as e:
            # Non-blocking if artifact service is not attached in some standalone runners
            print(f"Note: tool_context.save_artifact notice: {e}")

        # 3. Upload raw bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(img_bytes, content_type="image/png")

        public_image_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "image_url": public_image_url,
            "artifact_filename": filename,
            "artifact_version": artifact_version,
            "message": "Recovery roadmap image generated, saved as artifact, and published to Cloud Storage.",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate recovery image: {str(e)}",
        }
