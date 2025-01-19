from celery import Celery
import requests
import httpx

celery = Celery("workers")
celery.conf.broker_url = "redis://localhost:6379/0"
celery.conf.result_backend = "redis://localhost:6379/0"

# Optimization for batch processing
celery.conf.worker_prefetch_multiplier = 1  # Prevent task reservation
celery.conf.task_acks_late = True           # Acknowledge tasks only after completion


@celery.task(bind=True, soft_time_limit=1000, time_limit=1030)  # bind=True to access self.retry
def transcribe_audio(self, audio_url, merged_audio_id, store_name, source_type="url"):
    """
    Sends an audio file to the transcription API.
    Retries up to 3 times on failure and logs results.
    """
    api_endpoint = "http://localhost:8000/sarvam/transcribe"  # FastAPI endpoint
    target_api_endpoint = "http://dashboard.cur8.in:8081/api/update_db_transcript/"
    
    timeout = (30, 900)
    try:
        # Post to the transcription API
        response = requests.post(
            api_endpoint,
            data={
                "source_type": (None, source_type),
                "audio_url": (None, audio_url)
            },
            timeout=timeout
        )
        response.raise_for_status()
        transcription_result = response.json()  # Get the transcription result

        # Add merged_audio_id and store_name to the transcription result
        transcription_result["merged_audio_id"] = merged_audio_id
        transcription_result["store_name"] = store_name
        transcription_result["access_url_chunks"] = audio_url

        # # Optionally post the transcription result to a second API
        # post_response = requests.post(
        #     target_api_endpoint,
        #     json=transcription_result,  # Send the transcription result in JSON format
        #     timeout=120
        # )
        # post_response.raise_for_status()

        return transcription_result

    except requests.exceptions.ReadTimeout:
        raise self.retry(countdown=30, max_retries=5)  # Retry with backoff
    except requests.exceptions.RequestException as exc:
        raise self.retry(exc=exc, countdown=30)
