from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
# Importing NoResultFound for error handling of query
from sqlalchemy.orm.exc import NoResultFound
from database_setup import Base, Genre, Song, User
# import for anti forgery state token
from flask import session as login_session
# IMPORTS FOR gconnect
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from flask import make_response
# Import required for function decorator. See: login_required()
from functools import wraps
import datetime
import random
import string
import httplib2
import json
import requests
import os
from flask import Flask, render_template, request, redirect, jsonify, \
    url_for, flash


app = Flask(__name__)

app_dir = os.path.dirname(__file__) 

CLIENT_ID = json.loads(
    open(app_dir + '/client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu App"


# Connect to Database and create database session
engine = create_engine('postgresql://catalog:catalog@localhost/music')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

#####################################
#
# USER Helper Functions
#
#####################################


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Login decorator function
# Source: http://flask.pocoo.org/docs/0.10/patterns/viewdecorators/
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
        else:
            flash("Access Denied: Please login first.")
            return redirect('/login')
    return decorated_function

######################################
#
# Login and logout
#
#####################################
# Create a state token to prevent request forgery
# Store it in the session for later validation


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase +
                                  string.digits) for x in xrange(32))
    login_session['state'] = state
    # return 'The current session state is %s' %login_session['state']
    genres = session.query(Genre).order_by(asc(Genre.name))

    return render_template('login.html', STATE=state, genres=genres)

# Google Sign in


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(app_dir + '/client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already'
                                            'connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # See if user exists, it it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '  # noqa
    flash("You are now logged in as %s" % login_session['username'])
    return output


# Google Sign out
# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # print login_session['credentials']
    print login_session.get('access_token')

    access_token = login_session['access_token']

    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']

    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % \
        login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result

    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for'
                                            'given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Facebook Sign in
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open(app_dir + '/fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open(app_dir + '/fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)  # noqa
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly
    # logout, let's strip out the information before the equals sign
    # in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token  # noqa
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '  # noqa

    flash("You are now logged in as %s" % login_session['username'])
    return output


# Facebook sign out
@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id, access_token)  # noqa
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


# Disconnect based on provider
@app.route('/logout')
def logout():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['access_token']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showGenres'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showGenres'))


#######################################
#
# JSON APIs to view Music Information
#
#######################################
@app.route('/genre/<int:genre_id>/JSON')
def genreJSON(genre_id):
    genre = session.query(Genre).filter_by(id=genre_id).one()
    songs = session.query(Song).filter_by(genre_id=genre_id).all()
    return jsonify(songs=[i.serialize for i in songs])


@app.route('/genre/<int:genre_id>/song/<int:song_id>/JSON')
def songJSON(genre_id, song_id):
    try:
        song = session.query(Song).filter_by(id=song_id,
                                             genre_id=genre_id).one()
    # Adding error handling if no result is found.
    except NoResultFound:
        return jsonify({'error': 'Genre and song do not match!'})

    return jsonify(song.serialize)


@app.route('/genre/JSON')
def allGenreJSON():
    genres = session.query(Genre).all()
    return jsonify(genres=[i.serialize for i in genres])


############################
#
# Template rendering
#
############################
# Show all genres
@app.route('/')
def showGenres():
    songs = session.query(Song).order_by(asc(Song.name))
    genres = session.query(Genre).order_by(asc(Genre.name))
    return render_template('main.html', songs=songs, genres=genres)


@app.route('/genre/<int:genre_id>/')
def showGenreSongs(genre_id):
    genres = session.query(Genre).order_by(asc(Genre.name))
    songs = session.query(Song).filter_by(genre_id=genre_id)
    current_genre = session.query(Genre).filter_by(id=genre_id).one()
    return render_template('public_songs.html', genres=genres, songs=songs,
                           curr_genre=current_genre)


# user added songs list
@app.route('/mymusic')
# Check if user is logged in
@login_required
def userSongs():
    genres = session.query(Genre).order_by(asc(Genre.name))
    user_id = getUserID(login_session['email'])
    songs = session.query(Song).filter_by(user_id=user_id).all()

    return render_template('user_songs.html', genres=genres, songs=songs)


# Add Song
@app.route('/add-song/', methods=['GET', 'POST'])
# Check if user is logged in
@login_required
def addSong():
    genres = session.query(Genre).order_by(asc(Genre.name))

    if request.method == 'POST':
        if request.form['youtube_url']:
            # Decided to be more user friendly and ask users to enter a
            # youtube url. Since the url is consistent and only the query_id
            # changes, I extract the query id from the url
            youtube_id = request.form['youtube_url'].split("v=", 1)[1]
        if request.form['genre_id']:
            genre_id = request.form['genre_id']

        user_id = getUserID(login_session['email'])

        new_song = Song(name=request.form['song-name'],
                        artist_name=request.form['artist-name'],
                        youtube_id=youtube_id,
                        genre_id=genre_id,
                        user_id=user_id)
        session.add(new_song)
        session.commit()
        flash('Successfully Added %s - %s'
              % (new_song.name, new_song.artist_name))
        return redirect(url_for('userSongs'))
    else:
        return render_template('addsong.html', genres=genres)


@app.route('/genre/<int:genre_id>/song/<int:song_id>/edit',
           methods=['GET', 'POST'])
# Check if user is logged in
@login_required
def editSong(genre_id, song_id):
    editedSong = session.query(Song).filter_by(id=song_id).one()

    luser_id = getUserID(login_session['email'])
    if editedSong.user_id != luser_id:
        # Redirect to homepage if user ids do not match
        return '''<script>
            function myFunction() {
                alert('You are not authorized to edit this song.');
                window.location.replace('/');
                }
        </script>
        <body onload='myFunction()'>'''

    genre = session.query(Genre).filter_by(id=genre_id).one()
    genres = session.query(Genre).order_by(asc(Genre.name))

    if request.method == 'POST':
        if request.form['song-name']:
            editedSong.name = request.form['song-name']
        if request.form['artist-name']:
            editedSong.artist_name = request.form['artist-name']
        if request.form['youtube_url']:
            # Decided to be more user friendly and ask users to enter a
            # youtube url. Since the url is consistent and only the query_id
            # changes, I extract the query id from the url
            youtube_id = request.form['youtube_url'].split("v=", 1)[1]
            editedSong.youtube_id = youtube_id
        if request.form['genre_id']:
            editedSong.genre_id = request.form['genre_id']
        session.add(editedSong)
        session.commit()
        flash('Successfully Edited %s - %s' % (editedSong.name,
                                               editedSong.artist_name))
        return redirect(url_for('userSongs'))
    else:
        return render_template('editsong.html', genre=genre, genres=genres,
                               song=editedSong)


# Delete a song
@app.route('/genre/<int:genre_id>/song/<int:song_id>/delete',
           methods=['GET', 'POST'])
# Check if user is logged in
@login_required
def deleteSong(genre_id, song_id):
    itemToDelete = session.query(Song).filter_by(id=song_id).one()

    luser_id = getUserID(login_session['email'])
    if itemToDelete.user_id != luser_id:
        # Redirect to homepage if user ids do not match
        return '''<script>
            function myFunction() {
                alert('You are not authorized to delete this song.');
                window.location.replace('/');
                }
        </script>
        <body onload='myFunction()'>'''

    genre = session.query(Genre).filter_by(id=genre_id).one()
    genres = session.query(Genre).order_by(asc(Genre.name))

    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Successfully Deleted %s - %s' % (itemToDelete.name,
                                                itemToDelete.artist_name))
        return redirect(url_for('userSongs'))
    else:
        return render_template('deletesong.html', song=itemToDelete,
                               genres=genres)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
