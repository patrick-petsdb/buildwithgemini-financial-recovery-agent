"""Video generation tool for Financial Scam Recovery Agent.

Uses Google's Omni model (gemini-omni-flash-preview) in the global region.
Saves the generated video as an ADK artifact (Playground Artifacts panel)
and uploads it to the public Cloud Storage bucket.
"""

import base64
import time
import uuid
from typing import Any
from google import genai
from google.adk.tools.tool_context import ToolContext
from google.cloud import storage
from google.genai import types

PROJECT_ID = "qwiklabs-gcp-03-44680d3a8b6a"
BUCKET_NAME = "financial-recovery-assets-qwiklabs-gcp-03-44680d3a8b6a"


async def generate_recovery_guidance_video(
    prompt: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Generate a short video animation for a scam recovery guide or milestone.

    Generates the video using Google's Omni model (gemini-omni-flash-preview) in the global region,
    saves the video bytes as an ADK session artifact so it appears in the Playground's Artifacts panel,
    uploads the same video bytes to the public Cloud Storage bucket, and returns the public HTTPS URL.

    Args:
        prompt: Description of the recovery or security animation to generate (e.g., 'A calming 3D
                motion graphic of a digital shield locking down unauthorized transactions, then
                displaying a verified badge with a checklist').
        tool_context: ADK ToolContext injected by the runtime for saving session artifacts.

    Returns:
        A dictionary containing the public HTTPS video URL, artifact filename, and status.
    """
    try:
        # 1. Initialize GenAI client configured for Vertex AI in global location
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

        enhanced_prompt = (
            f"{prompt}. High quality, clean modern motion graphics, calm reassuring financial recovery visual."
        )

        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=enhanced_prompt,
            response_format={"type": "video"},
        )

        video_output = getattr(interaction, "output_video", None)
        if not video_output:
            return {
                "status": "error",
                "message": "Model did not return video output in the interaction response.",
            }

        video_bytes = None
        mime_type = getattr(video_output, "mime_type", "video/mp4") or "video/mp4"

        if getattr(video_output, "data", None):
            raw_data = video_output.data
            if isinstance(raw_data, str):
                video_bytes = base64.b64decode(raw_data)
            else:
                video_bytes = raw_data
        elif getattr(video_output, "uri", None):
            downloaded = client.files.download(file=video_output.uri)
            video_bytes = downloaded

        if not video_bytes:
            return {
                "status": "error",
                "message": "Failed to extract video bytes from the model output.",
            }

        filename = f"recovery_video_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp4"

        # 2. Save video as an ADK session artifact for Playground panel
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        artifact_version = None
        try:
            artifact_version = await tool_context.save_artifact(
                filename=filename, artifact=artifact_part
            )
        except Exception as e:
            print(f"Note: tool_context.save_artifact notice: {e}")

        # 3. Upload raw bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_video_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "video_url": public_video_url,
            "artifact_filename": filename,
            "artifact_version": artifact_version,
            "message": "Recovery guidance video generated, saved as artifact, and published to Cloud Storage.",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate video: {str(e)}",
        }
