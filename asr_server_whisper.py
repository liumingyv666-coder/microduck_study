import os
import tempfile

from fastapi import FastAPI, File, UploadFile
from faster_whisper import WhisperModel

app = FastAPI()
model = WhisperModel(
    os.environ.get("WHISPER_MODEL", "small"),
    device=os.environ.get("WHISPER_DEVICE", "cuda"),
    compute_type=os.environ.get("WHISPER_COMPUTE", "float16"),
)


@app.post("/asr")
async def asr(file: UploadFile = File(...)):
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        segments, _ = model.transcribe(
            path, language="zh", beam_size=1, vad_filter=True
        )
        text = "".join(segment.text for segment in segments).strip()
    finally:
        os.unlink(path)
    return {"text": text}
