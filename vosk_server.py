import io
import json
import os
import wave

import vosk
from fastapi import FastAPI, File, UploadFile

MODEL = os.environ.get(
    "VOSK_MODEL", r"C:\Users\27994\models\vosk-model-small-cn-0.22"
)
model = vosk.Model(MODEL)
app = FastAPI()


@app.post("/asr")
async def asr(file: UploadFile = File(...)):
    data = await file.read()
    with wave.open(io.BytesIO(data), "rb") as wav:
        rec = vosk.KaldiRecognizer(model, wav.getframerate())
        text = ""
        while True:
            chunk = wav.readframes(4000)
            if not chunk:
                break
            if rec.AcceptWaveform(chunk):
                text += json.loads(rec.Result()).get("text", "")
        text += json.loads(rec.FinalResult()).get("text", "")
    return {"text": text.strip()}
