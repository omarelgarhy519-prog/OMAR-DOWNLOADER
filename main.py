from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import yt_dlp, tempfile, os, mimetypes

app=FastAPI(title="OMAR DOWNLOADER API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Info(BaseModel):
    url: HttpUrl

def opts():
    return {"quiet":True,"no_warnings":True,"noplaylist":True}

@app.post("/api/info")
def info(data: Info):
    try:
        with yt_dlp.YoutubeDL(opts()) as y:
            x=y.extract_info(str(data.url), download=False)
        return {"title":x.get("title"),"site":x.get("extractor_key"),"duration":x.get("duration"),"thumbnail":x.get("thumbnail")}
    except Exception as e:
        raise HTTPException(400, f"تعذر تحليل الرابط: {str(e)[:300]}")

@app.get("/api/download")
def download(url: str=Query(...), format: str=Query("video"), quality: str=Query("best")):
    if not url.startswith(("http://","https://")):
        raise HTTPException(400,"الرابط غير صحيح")
    tmp=tempfile.mkdtemp(prefix="omar_dl_")
    try:
        if format=="audio":
            out=os.path.join(tmp,"audio.%(ext)s")
            o=opts()|{"format":"bestaudio/best","outtmpl":out,"postprocessors":[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}]}
        else:
            q="bestvideo+bestaudio/best"
            if quality in ("720","480"): q=f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
            o=opts()|{"format":q,"outtmpl":os.path.join(tmp,"video.%(ext)s"),"merge_output_format":"mp4"}
        with yt_dlp.YoutubeDL(o) as y:
            y.download([url])
        files=os.listdir(tmp)
        if not files: raise RuntimeError("لم يتم إنشاء ملف")
        p=os.path.join(tmp,files[0])
        media=mimetypes.guess_type(p)[0] or "application/octet-stream"
        def stream():
            try:
                with open(p,"rb") as f:
                    while chunk:=f.read(1024*1024): yield chunk
            finally:
                try:
                    for f in os.listdir(tmp): os.remove(os.path.join(tmp,f))
                    os.rmdir(tmp)
                except: pass
        return StreamingResponse(stream(),media_type=media,headers={"Content-Disposition":f'attachment; filename="omar-downloader.{p.rsplit(".",1)[-1]}"'})
    except Exception as e:
        try:
            for f in os.listdir(tmp): os.remove(os.path.join(tmp,f))
            os.rmdir(tmp)
        except: pass
        raise HTTPException(400,f"فشل التنزيل: {str(e)[:400]}")

@app.get("/health")
def health(): return {"ok":True,"app":"OMAR DOWNLOADER"}
