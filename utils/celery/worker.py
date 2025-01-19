from celery_app import celery

celery.conf.update(
    task_routes={
        'celery_app.transcribe_audio': 'audio_transcription',
    }
)

if __name__ == "__main__":
    celery.start()