from app.services.transcript_service import TranscriptService

service = TranscriptService()

url = "https://youtu.be/lQRsqMiBTsI?si=yltC7saacK_5mxCg"

data = service.get_transcript(url)

print(data["video_id"])
print(data["title"])
print(data["transcript"][:500])