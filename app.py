import logging
import requests
import os
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from starlette.middleware.trustedhost import TrustedHostMiddleware
import time
from utils.sarvam.sarvam_helper import transcribe_with_sarvam
from parameters import transcripts_collection, task_tracker, s3_client, AWS_BUCKET_NAME, append_log_to_db
from datetime import datetime
from werkzeug.utils import secure_filename
from io import BytesIO
import uuid
from bson import ObjectId

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Sarvam Transcription API", description="API for audio transcription using Sarvam AI")


# Middleware for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for trusted hosts
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*", "localhost"])


@app.middleware("http")
async def add_request_logging(request: Request, call_next):
    logging.info(f"Incoming request: {request.method} {request.url}")
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logging.info(f"Processed request: {request.method} {request.url} in {duration:.2f} seconds with status {response.status_code}")
    return response


@app.post("/sarvam/transcribe")
async def upload_audio_for_transcription(
    request: Request,
    audio: UploadFile = File(None)
):
    try:
        # Extract source type from request
        form_data = await request.form()
        source_type = form_data.get("source_type")

        if not source_type:
            return JSONResponse(content={"error": "Source type (file or url) is required"}, status_code=400)

        if source_type == 'file':
            response = await handle_file_upload(audio)

        elif source_type == 'url':
            audio_url = form_data.get("audio_url")
            print(0)
            response = await handle_url_upload(audio_url)
            print(response)

        else:
            return JSONResponse(content={"error": "Invalid source type. Please specify either 'file' or 'url'."}, status_code=400)

        lang = await get_audio_for_transcription(response['s3_key'])
        return lang

    except Exception as e:
        logging.error(f"Error in transcribe_audio_with_sarvam API: {str(e)}")
        return JSONResponse(content={"error": f"Server Error: {str(e)}"}, status_code=500)

async def handle_file_upload(audio: UploadFile):
    """Handles file-based audio uploads."""
    if not audio:
        return {"error": "No file part"}

    if audio.filename == '':
        return {"error": "No selected file"}

    if not audio.filename.endswith(('.wav', '.mp3')):
        return {"error": "Invalid file type. Only WAV and MP3 files are allowed."}

    filename = secure_filename(audio.filename)
    s3_key = f"temp/{uuid.uuid4()}/{filename}"

    try:
        # Read the audio file into memory
        file_content = await audio.read()
        
        # Convert the bytes into a file-like object
        file_obj = BytesIO(file_content)

        # Upload to S3
        s3_client.upload_fileobj(file_obj, AWS_BUCKET_NAME, s3_key)
        
    except Exception as e:
        return {"error": f"Failed to upload to S3: {str(e)}"}

    # Simulate S3 upload (replace with actual implementation)
    logging.info(f"Uploading file {filename} to S3 with key {s3_key}")

    # transcript_record = {
    #     "s3_key": s3_key,
    #     "status": "queued",
    #     "timestamp": datetime.utcnow(),
    #     "file_name": filename,
    #     "type": "sarvam"
    # }

    # transcript_id = transcripts_collection.insert_one(transcript_record).inserted_id

    return {
        "message": "Audio file uploaded successfully",
        # "transcript_id": str(transcript_id),
        "s3_key": s3_key,
        "status": "queued"
    }

async def handle_url_upload(audio_url: str):
    """Handles URL-based audio uploads."""
    if not audio_url:
        return {"error": "Audio URL is required when source type is 'url'"}

    try:
        response = requests.get(audio_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to download the audio from URL: {str(e)}"}

    audio_data = BytesIO(response.content)
    filename = os.path.basename(audio_url.split('?')[0])
    s3_key = f"temp/{uuid.uuid4()}/{filename}"

    try:
        logging.info(f"Uploading audio from URL {audio_url} to S3 with key {s3_key}")

        # Upload to S3
        s3_client.upload_fileobj(audio_data, AWS_BUCKET_NAME, s3_key)
        
    except Exception as e:
        return {"error": f"Failed to upload to S3: {str(e)}"}

    # transcript_record = {
    #     "s3_key": s3_key,
    #     "status": "queued",
    #     "timestamp": datetime.utcnow(),
    #     "file_name": filename,
    #     "type": "sarvam"
    # }

    # transcript_id = transcripts_collection.insert_one(transcript_record).inserted_id

    return {
        "message": "Audio file from URL processed successfully",
        # "transcript_id": str(transcript_id),
        "s3_key": s3_key,
        "status": "queued"
    }


async def get_audio_for_transcription(
    s3_key: str, 
    language_code: str = Form(""),
    model: str = Form("saarika:v2"),
    with_diarization: bool = Form(True),
    with_timestamps: bool = Form(False),
):
    try:
        
        # append_log_to_db(transcript_id, "INFO", "Started transcription process")

        # task_tracker.insert_one({
        #     'transcript_id': transcript_id,
        #     'status': 'in-progress',
        #     'type': 'sarvam'
        # })

        # transcripts_collection.update_one(
        #     {"_id": ObjectId(transcript_id)},
        #     {"$set": {"status": "in-progress"}}
        # )

        # if not s3_key:
            # append_log_to_db(transcript_id, "ERROR", "Missing S3 key in the document")

        current_dir = os.getcwd()
        local_file_path = os.path.join(current_dir, f"audio/{s3_key.split('/')[-1]}")
        try:
            s3_object = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=s3_key)

            audio_data = s3_object['Body'].read()
            # audio_file = BytesIO(audio_data)

            # append_log_to_db(transcript_id, "INFO", f"Sending file {s3_key} to sarvam API")
            # task_tracker.update_one(
            #     {'transcript_id': transcript_id},
            #     {"$set": {"status": "queued", "type": "sarvam"}}
            # )
    
            response = await transcribe_with_sarvam(
                audio_data,
            )

            if response["message"] == "success":
                logging.info("Transcription successful for the uploaded file")

                audio_segments = response.get("audio_segments", "")
                full_transcription = response.get("full_transcription", "")
                full_diarization = response.get("full_diarization", [])
                translated_transcript =  response.get("translated_transcript", "")

                final_response = {"results": {
                    "transcripts": full_transcription,
                    "translated_transcript" : translated_transcript,
                    "audio_segments": audio_segments,
                }}

                # append_log_to_db(transcript_id, "INFO", "Transcription and diarization completed successfully.")
                # transcripts_collection.update_one(
                #     {"_id": ObjectId(transcript_id)},
                #     {"$set": {
                #         "status": "completed",
                #         "results": {
                #             "audio_segments": audio_segments,
                #             "full_transcription": full_transcription,
                #             "full_diarization": full_diarization
                #         }
                #     }}
                # )

                # append_log_to_db(transcript_id, "INFO", "Results saved to database.")
                # task_tracker.update_one(
                #     {'transcript_id': transcript_id},
                #     {"$set": {"status": "completed"}}
                # )
                return final_response
            else:
                logging.error("Transcription failed: %s", response["error"])
                error_message = f"Error from sarvam API: {response.text}"
                # append_log_to_db(transcript_id, "ERROR", error_message)
                # transcripts_collection.update_one(
                #     {"_id": ObjectId(transcript_id)},
                #     {"$set": {"status": "failed", "error": error_message}}
                # )
                # task_tracker.update_one(
                #     {'transcript_id': transcript_id},
                #     {"$set": {"status": "failed"}}
                # )
                raise HTTPException(status_code=500, detail=response["error"])

        except Exception as e:
            logging.error("HTTPException: %s", e.detail)
            # error_message = f"Error processing transcript {transcript_id}: {str(e)}"
            # append_log_to_db(transcript_id, "ERROR", error_message)
            # transcripts_collection.update_one(
            #     {"_id": ObjectId(transcript_id)},
            #     {"$set": {"status": "failed", "error": str(e)}}
            # )
            # task_tracker.update_one(
            #     {'transcript_id': transcript_id},
            #     {"$set": {"status": "failed"}}
            # )
            raise e

        finally:
            if os.path.exists(local_file_path):
                try:
                    os.remove(local_file_path)
                    # append_log_to_db(transcript_id, "INFO", f"Deleted local file: {local_file_path}")
                except Exception as e:
                    pass
                    # append_log_to_db(transcript_id, "ERROR", f"Error deleting local file: {str(e)}")
        # print(7)

    except Exception as e:
        logging.error("Unexpected error during transcription: %s", str(e))
        # append_log_to_db("global", "ERROR", f"Error during execution: {str(e)}")
        return {"error":"failed"}


# @app.post("/sarvam/transcribe")
# async def transcribe_audio_with_sarvam(
#     language_code: str = Form("hi-IN"),
#     model: str = Form("saarika:v2"),
#     with_diarization: bool = Form(True),
#     with_timestamps: bool = Form(False),
#     audio: UploadFile = File(...)
# ):
#     try:
#         logging.info("Received file for transcription: %s", audio.filename)

#         if not audio.filename.endswith(('.wav', '.mp3')):
#             logging.warning("Unsupported file format: %s", audio.filename)
#             raise HTTPException(status_code=400, detail="Only WAV and MP3 formats are supported.")

#         audio_data = await audio.read()

#         logging.info("Language code: %s", language_code)

#         response = await transcribe_with_sarvam(
#             audio_data,
#             language_code,
#             model,
#             with_diarization,
#             with_timestamps
#         )

#         if "error" not in response:
#             logging.info("Transcription successful for file: %s", audio.filename)

#             # Ensure the response is JSON and support encoding for all languages
#             return JSONResponse(content=response, media_type="application/json")
#         else:
#             logging.error("Transcription failed: %s", response["error"])
#             raise HTTPException(status_code=500, detail=response["error"])
#     except HTTPException as e:
#         logging.error("HTTPException: %s", e.detail)
#         raise e
#     except Exception as e:
#         logging.error("Unexpected error during transcription: %s", str(e))
#         raise HTTPException(status_code=500, detail="An unexpected error occurred during transcription.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)





