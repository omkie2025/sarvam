import asyncio
from fastapi import HTTPException
import logging
import httpx
import math
import io
from pydub import AudioSegment
# from utils.logs.log_helper import log_execution_time
from utils. configs.config import SARVAM_API_URL, SARVAM_API_KEY
from openai import OpenAI
import openai
import os
openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()


async def transcribe_with_sarvam(audio_data: bytes) -> dict:
    try:
        logging.info("Starting transcription with Sarvam for audio data of size: %d bytes", len(audio_data))

        # Validate input type
        if not isinstance(audio_data, bytes):
            logging.error("Invalid input type: Expected bytes, got %s", type(audio_data).__name__)
            raise TypeError(f"Expected bytes-like object for audio_data, got {type(audio_data).__name__}")

        # Define max chunk duration in seconds (5 minutes)
        MAX_CHUNK_DURATION = 300

        # Load audio data using pydub
        audio = AudioSegment.from_file(io.BytesIO(audio_data), format="wav")
        audio_duration = len(audio) / 1000  # Convert duration to seconds
        logging.info("Loaded audio file with duration: %.2f seconds", audio_duration)

        # If audio is shorter than the max duration, process it directly
        if audio_duration <= MAX_CHUNK_DURATION:
            logging.info("Audio is shorter than max chunk duration; processing directly")
            return await transcribe_chunk(audio_data)

        # Otherwise, split the audio into chunks
        logging.info("Audio exceeds max chunk duration; splitting into chunks")
        chunks = []
        num_chunks = math.ceil(audio_duration / MAX_CHUNK_DURATION)

        for i in range(num_chunks):
            start_ms = i * MAX_CHUNK_DURATION * 1000
            end_ms = min((i + 1) * MAX_CHUNK_DURATION * 1000, len(audio))
            chunk = audio[start_ms:end_ms]
            chunk_data = io.BytesIO()
            chunk.export(chunk_data, format="wav")
            chunks.append(chunk_data.getvalue())
            logging.info("Created chunk %d/%d: Start=%.2f seconds, End=%.2f seconds", i + 1, num_chunks, start_ms / 1000, end_ms / 1000)

        # Transcribe each chunk concurrently
        logging.info("Starting concurrent transcription of %d chunks", num_chunks)
        tasks = [transcribe_chunk(chunk_data) for chunk_data in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results
        all_segments = []
        full_transcription = ""
        translated_transcript = ""

        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error("Error processing chunk %d: %s", idx + 1, result)
                continue
            logging.info("Successfully processed chunk %d", idx + 1)
            all_segments.extend(result["audio_segments"])
            full_transcription += result["full_transcription"]["transcript"] + " "

            # Include the translated transcription if it exists
            if "translated_transcript" in result:
                translated_transcript += result["translated_transcript"] + " "

        # Prepare final result
        result = {
            "message": "success",
            "audio_segments": all_segments,
            "full_transcription": {"transcript": full_transcription.strip()},
            "full_diarization": all_segments,
            "translated_transcript": translated_transcript.strip() if translated_transcript else None,
            "lang": " "  # Language merging logic can be added if needed
        }

        logging.info("Successfully completed transcription with %d chunks processed", num_chunks)
        return result

    except TypeError as e:
        logging.error("Type error: %s", str(e))
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        logging.error("Unexpected error during transcription: %s", str(e))
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


# @log_execution_time
async def transcribe_chunk(audio_data: bytes) -> dict:
    try:
        logging.info("Starting transcription for a chunk of size: %d bytes", len(audio_data))

        # Prepare the file and data payload
        files = {
            "file": ("audio.wav", audio_data, "audio/wav")  # Explicitly set the MIME type
        }
        data = {
            "model": "saarika:v2",
            "with_diarization": "true",
            "with_timestamps": "true"
        }
        headers = {
            "api-subscription-key": SARVAM_API_KEY
        }

        # Set a custom timeout for the request
        timeout =  httpx.Timeout(
            connect=30.0,   # Max time to establish a connection
            write=30.0,     # Max time to send audio chunk
            read=420.0,     # Max time to receive transcription (7 minutes per chunk)
            pool=300.0      # Max time to reuse connection
        )

        logging.info("Sending request to Sarvam API at %s", SARVAM_API_URL)

        # Send the request to the Sarvam API
        async with httpx.AsyncClient() as client:
            response = await client.post(SARVAM_API_URL, headers=headers, files=files, data=data, timeout=timeout)

        # Raise an exception for HTTP errors
        response.raise_for_status()

        # Parse the response as JSON
        response_data = response.json()

        logging.info("Received response from Sarvam API: %s", response.status_code)

        # Parse and format response
        utterances = response_data.get("diarized_transcript", {}).get("entries", [])
        transcription_result = response_data.get("transcript", "")
        full_transcription = {"transcript": transcription_result}

        # Format utterances into the desired structure
        audio_segments = []
        for utterance in utterances:
            # Check if the utterance needs translation
            transcript = utterance.get("transcript", "")
            translated_transcript = await translate_text(transcript, response_data.get("language_code", " ")) if response_data.get("language_code", " ") not in ["en-IN", "hi-IN"] else ""

            # Format each utterance
            segment = {
                "start_time": utterance.get("start_time_seconds"),
                "end_time": utterance.get("end_time_seconds"),
                "speaker_label": f"spk_{utterance.get('speaker_id')}",
                "transcript": transcript,
                "": translated_transcript,
                # "translated_transcript": translated_transcript
            }
            audio_segments.append(segment)

        # Prepare final result
        result = {
            "message": "success",
            "audio_segments": audio_segments,
            "full_transcription": full_transcription,
            "full_diarization": audio_segments,
            "lang": response_data.get("language_code", " ")
        }

        # Check language code and if not English or Hindi, translate using GPT-4 model
        language_code = response_data.get("language_code", "").lower()
        if language_code not in ["en", "hi"]:
            # Translate the full transcription using GPT-4 model
            translated_transcript = await translate_text(full_transcription["transcript"], language_code)
            result["translated_transcript"] = translated_transcript
            logging.info("Translated diarized transcript added for language code: %s", language_code)

        logging.info("Successfully completed transcription for the chunk")
        return result

    except httpx.ReadTimeout:
        logging.error("Timeout occurred while waiting for Sarvam API response")
        raise HTTPException(status_code=504, detail="The request to Sarvam API timed out.")
    except httpx.RequestError as e:
        logging.error("Request error while communicating with Sarvam API: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error communicating with Sarvam API: {e}")
    except Exception as e:
        print(response.json())
        logging.error("Unexpected error during chunk transcription: %s", str(e))
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


async def translate_text(text: str, source_lang: str) -> str:
    """
    Translates text to English using a model like GPT-4 or any translation API.
    You can replace this with the translation logic of your choice.
    """
    try:
        translation = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {
                    "role": "system",
                    "content": f"You are a translator that translates text from {source_lang} to English:\n\n{text}"
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            max_tokens=1024
        )
        return translation.choices[0].message.content
    except Exception as e:
        logging.error("Error during translation with GPT-4: %s", str(e))
        return ""  
