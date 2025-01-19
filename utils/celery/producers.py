import requests
from celery_app import transcribe_audio
from celery import group

API_ENDPOINT = {
  "access_urls": [
    {
      "merged_audio_id": 397,
      "store_name": "BLR",
      "access_url_chunks": [
        "https://sherpa-retail-recording.s3.amazonaws.com/wakefit/chunks/2025-01-15/45/conversation_12-13-32_12-23-38.wav?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXDHCUEQSNBMWYIDQ%2F20250115%2Fap-south-1%2Fs3%2Faws4_request&X-Amz-Date=20250115T232640Z&X-Amz-Expires=604799&X-Amz-SignedHeaders=host&X-Amz-Signature=b6055fd31f28a08f4fa60e4d97726a5281a1299e0b4758041852028baf4b9296",
        "https://sherpa-retail-recording.s3.amazonaws.com/wakefit/chunks/2025-01-15/45/conversation_08-51-06_09-07-29.wav?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXDHCUEQSNBMWYIDQ%2F20250115%2Fap-south-1%2Fs3%2Faws4_request&X-Amz-Date=20250115T232640Z&X-Amz-Expires=604799&X-Amz-SignedHeaders=host&X-Amz-Signature=f1c8f5709458a715671d47b5c74d082dbba7169c29a4f6e7fb7430c800e639e9",
        "https://sherpa-retail-recording.s3.amazonaws.com/wakefit/chunks/2025-01-15/45/conversation_08-48-29_08-48-53.wav?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXDHCUEQSNBMWYIDQ%2F20250115%2Fap-south-1%2Fs3%2Faws4_request&X-Amz-Date=20250115T232640Z&X-Amz-Expires=604799&X-Amz-SignedHeaders=host&X-Amz-Signature=e63ad64a29fc8155ceb62ae026c4c5051d92b878376c2bee22446503b155996f"
      ]
    },
    {
      "merged_audio_id": 395,
      "store_name": "BLR",
      "access_url_chunks": [
        "https://sherpa-retail-recording.s3.amazonaws.com/wakefit/chunks/2025-01-15/61/conversation_08-57-40_09-24-59.wav?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXDHCUEQSNBMWYIDQ%2F20250115%2Fap-south-1%2Fs3%2Faws4_request&X-Amz-Date=20250115T232245Z&X-Amz-Expires=604799&X-Amz-SignedHeaders=host&X-Amz-Signature=8c3fc065b7cf7ee80ff5bb73ee2a2377a474faea79a0a6662c6d8475513770d5",
        "https://sherpa-retail-recording.s3.amazonaws.com/wakefit/chunks/2025-01-15/61/conversation_14-44-59_14-45-18.wav?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXDHCUEQSNBMWYIDQ%2F20250115%2Fap-south-1%2Fs3%2Faws4_request&X-Amz-Date=20250115T232245Z&X-Amz-Expires=604799&X-Amz-SignedHeaders=host&X-Amz-Signature=ea7d580bb1e052544c18705ff807790fb794282784c100c32fb270b305629553",
        "https://sherpa-retail-recording.s3.amazonaws.com/wakefit/chunks/2025-01-15/61/conversation_10-19-59_10-37-23.wav?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXDHCUEQSNBMWYIDQ%2F20250115%2Fap-south-1%2Fs3%2Faws4_request&X-Amz-Date=20250115T232245Z&X-Amz-Expires=604799&X-Amz-SignedHeaders=host&X-Amz-Signature=24edf4ac9c2af8e93688c8e105b2f8ce0108a6cd3c8b8b753cef542a4cf2d71d",
        "https://sherpa-retail-recording.s3.amazonaws.com/wakefit/chunks/2025-01-15/61/conversation_12-21-37_13-29-23.wav?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXDHCUEQSNBMWYIDQ%2F20250115%2Fap-south-1%2Fs3%2Faws4_request&X-Amz-Date=20250115T232245Z&X-Amz-Expires=604799&X-Amz-SignedHeaders=host&X-Amz-Signature=afafe60c0c109e7661a63dcd79d6df150234ad6d83422d647946af9ded68365f",
        "https://sherpa-retail-recording.s3.amazonaws.com/wakefit/chunks/2025-01-15/61/conversation_07-31-16_07-34-29.wav?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXDHCUEQSNBMWYIDQ%2F20250115%2Fap-south-1%2Fs3%2Faws4_request&X-Amz-Date=20250115T232245Z&X-Amz-Expires=604799&X-Amz-SignedHeaders=host&X-Amz-Signature=2fd422de2acd85d004f251fca4adbe610da8f290aedf5cce281f72cdb93a9f46"
      ]
    }
  ]}

# API_ENDPOINT = "http://dashboard.cur8.in:8081/api/send_access_url/"

def fetch_audio_data():
    """
    Fetch audio data from the provided API endpoint.
    """
    try:
        response = requests.get(API_ENDPOINT, timeout=30)
        response.raise_for_status()
        return response.json()  # Assuming the API returns JSON
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch audio data: {e}")
        return None


def queue_tasks():
    """
    Fetch audio data from the API and queue transcription tasks in batches.
    """
    audio_data = API_ENDPOINT
    if not audio_data:
        print("No audio data fetched. Exiting.")
        return

    # Loop through the audio data and create a list of tasks
    access_urls = audio_data.get("access_urls", [])
    if not access_urls:
        print("No access URLs found in the audio data.")
        return

    task_batches = []
    for access_entry in access_urls:
        merged_audio_id = access_entry.get("merged_audio_id")
        store_name = access_entry.get("store_name")

        if not merged_audio_id or not store_name:
            print(f"Missing required data in access entry: {access_entry}")
            continue

        for audio_url in access_entry.get("access_url_chunks", []):
            if not audio_url:
                print(f"Skipping empty audio URL for {store_name} (ID: {merged_audio_id})")
                continue

            # Add tasks to the batch
            task_batches.append(
                transcribe_audio.s(audio_url, merged_audio_id, store_name)  # Add the task to the batch
            )

    # Divide tasks into chunks of 5 for batch processing
    for i in range(0, len(task_batches), 5):
        batch = task_batches[i:i + 5]
        print(f"Queueing batch with {len(batch)} tasks...")
        group(batch).apply_async(queue="audio_transcription")


if __name__ == "__main__":
    queue_tasks()