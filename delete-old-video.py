import datetime
import pickle
import time
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

CLIENT_SECRETS_FILE = 'client_secret.json'
TOKEN_FILE = 'token.pkl'
SCOPES = ['https://www.googleapis.com/auth/youtube']

def get_authenticated_service():
    try:
        with open(TOKEN_FILE, 'rb') as token:
            credentials = pickle.load(token)
    except FileNotFoundError:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        credentials = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
    return build('youtube', 'v3', credentials=credentials)

def delete_old_videos(youtube):
    now = datetime.datetime.now(datetime.timezone.utc)
    two_days_ago = now - datetime.timedelta(days=2)

    channels_response = youtube.channels().list(mine=True, part="contentDetails").execute()
    uploads_playlist_id = channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    playlist_request = youtube.playlistItems().list(
        playlistId=uploads_playlist_id,
        part="snippet",
        maxResults=50  
    )
    while playlist_request:
        playlist_response = playlist_request.execute()

        for item in playlist_response.get('items', []):
            video_id = item['snippet']['resourceId']['videoId']
            upload_date = datetime.datetime.strptime(item['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
            upload_date = upload_date.replace(tzinfo=datetime.timezone.utc)

            if upload_date < two_days_ago:
                delete_request = youtube.videos().delete(id=video_id)
                delete_request.execute()
                print(f"Deleted video {video_id}")

        playlist_request = youtube.playlistItems().list_next(playlist_request, playlist_response)

def main():
    youtube = get_authenticated_service()
    while True:
        delete_old_videos(youtube)
        print("Sleeping for 48 hours...")
        time.sleep(172800)  # Pause de 48 heures avant de relancer le script

if __name__ == "__main__":
    main()
