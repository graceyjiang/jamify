from flask import Flask, request, url_for, session, redirect, render_template
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time 
from time import gmtime, strftime
from spotipy.cache_handler import FlaskSessionCacheHandler
import ast

import os

app = Flask(__name__)
app.debug = True

CLIENT_ID = '3e8ea4047a99490ab60768bc5269bc53'
CLIENT_SECRET = '176396f3ac83433caef42abf302af117'
TOKEN_CODE = "token_info"


app.secret_key = 'O238746uoiueihns'
app.config['SESSION_COOKIE_NAME'] = 'Our Cookie'

cache_handler = FlaskSessionCacheHandler(session)

@app.route('/')
def index():
    return render_template('index.html')

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=url_for("callback",_external=True),
        scope="user-read-recently-played, playlist-modify-public, playlist-modify-private",
        cache_handler= cache_handler,
        
    )

@app.route('/login')
def login():
    sp_oauth = create_spotify_oauth()
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return redirect(url_for("ranking", _external=True))

def get_token(): 
    token_info = session.get(TOKEN_CODE, None)
    if not token_info: 
        raise "exception"
    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60 
    if (is_expired): 
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    return token_info 


@app.route('/callback')
def callback():
    sp_oauth = create_spotify_oauth()
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for("login", _external=True))
    

@app.route('/ranking', methods=["GET", "POST"])
def ranking():
    if request.method == 'POST':
        user_input_num = request.form["dot-amount"]
        session["user_input_num"] = user_input_num
        return redirect(url_for("playlist_name", _external=True, user_input_num= user_input_num)) #send user input num to create playlist
    return render_template('ranking-page.html')

@app.route('/playlistname')
def playlist_name():
    return render_template('playlist-name.html')

@app.route('/createplaylist', methods=["GET", "POST"])
def create_playlist():
    sp_oauth = create_spotify_oauth()
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    

    sp_oauth = create_spotify_oauth()
    sp = spotipy.Spotify(auth_manager = sp_oauth)
    num_tracks_to_visualise = 50
    last_played_tracks = sp.current_user_recently_played(limit = num_tracks_to_visualise)
    user_input_num = int(session.get("user_input_num"))
    max_valence_based_on_input = []
    if user_input_num == 1:
        max_valence_based_on_input = [0, 0.2]
    elif user_input_num == 2:
        max_valence_based_on_input = [0.2, 0.4]
    elif user_input_num == 3:
        max_valence_based_on_input = [0.4, 0.6]
    elif user_input_num == 4:
        max_valence_based_on_input = [0.6, 0.8]
    elif user_input_num == 5:
        max_valence_based_on_input = [0.8, 1]
    song_ids = []
    for track in last_played_tracks['items']:
        track_id = track['track']['id']
        token = get_token()['access_token']
        string = 'Bearer ' + token
        r = requests.get('https://api.spotify.com/v1/audio-features/' + track_id, headers={'Authorization': 'access_token '+ string})
        r = ast.literal_eval(r.text)
        if r["valence"] < max_valence_based_on_input[1] and r["valence"] > max_valence_based_on_input[0]:
            song_ids.append(track_id)

    recommended_tracks = sp.recommendations(seed_tracks=song_ids[:5])['tracks']
    recommendation_uris = []
    for i, track in enumerate(recommended_tracks):
        recommendation_uris.append(recommended_tracks[i]['uri'])
  
    user_id = sp.me()['id']
    user_input_playlist_name = request.form["fname"]
    playlist = sp.user_playlist_create(user_id, name=user_input_playlist_name, public=False, description="just what you're looking for")
    sp.playlist_add_items(playlist['id'], recommendation_uris)
    
    return render_template('create-playlist.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect("https://accounts.spotify.com")

if __name__ == '__main__':
    app.run(port=4455)