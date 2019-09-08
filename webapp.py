# Step 1: Importing libraries
from flask import Flask, redirect, url_for, session, request, jsonify
from flask_oauthlib.client import OAuth
from flask import render_template, flash, Markup


from github import Github

import pprint
import os
import sys
import traceback
import requests
import base64
import json

#List of files to replicate
FILES = [
'Procfile',
'README.md',
'random_string.py',
'requirements.txt',
'static/style.css',
'templates/flash_messages.html',
'templates/home.html',
'templates/layout.html',
'templates/navbar.html',
'webapp.py',
'.gitignore',
'Technical_Specifications.pdf',
'Installation_Document.pdf'
]



# Step 2: checking if the key variables are defined. They act as keys that need be 
# defined for the OAuth communication between this webapp and Github to work correctly. 
class GithubOAuthVarsNotDefined(Exception):
    '''raise this if the necessary env variables are not defined '''

if os.getenv('GITHUB_CLIENT_ID') == None or \
        os.getenv('GITHUB_CLIENT_SECRET') == None or \
        os.getenv('APP_SECRET_KEY') == None:
    print(os.getenv('GITHUB_CLIENT_ID'))
    print(os.getenv('GITHUB_CLIENT_SECRET'))
    print(os.getenv('APP_SECRET_KEY'))
    raise GithubOAuthVarsNotDefined('''
      Please define environment variables:
         GITHUB_CLIENT_ID
         GITHUB_CLIENT_SECRET
         GITHUB_ORG
         APP_SECRET_KEY
      ''')


# Step 3 : creating the app and setting the keys
app = Flask(__name__)
oauth = OAuth(app)
app.debug = False

app.secret_key = os.environ['APP_SECRET_KEY']
oauth = OAuth(app)

# Step 4: define the service to which delegating the login to (Github)
# OAuth requires certain URLs so that it knows where to send the user to be able
# to enter their account information.
github = oauth.remote_app(
    'github',
    consumer_key=os.environ['GITHUB_CLIENT_ID'],
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],
    request_token_params={'scope': 'public_repo'},
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize'
)

# Step 5: getting the token and secret 
@github.tokengetter
def get_github_oauth_token():
    return session.get('github_token')

# Step 6: Giving values to the related login variables
@app.context_processor
def inject_logged_in():
    return dict(logged_in=('github_token' in session))


# Step 7: rendering the webpages. login() and logout(), use our OAuth object to 
# log in and authorize a user by first calling the url for the function authorized() 
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    return github.authorize(callback=url_for('authorized', _external=True))

@app.route('/logout')
def logout():
    session.clear()
    flash('You were logged out!')
    return redirect(url_for('home'))


# Step 8 : resp is a variable that holds the message from Github after the user tries to log in. 
# HEre the code checks for several things and have error-handling so that our web 
# app produces information for our user to act upon.
@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()

    if resp is None:
        session.clear()
        login_error_message = 'Access denied: reason=%s error=%s full=%s' % (
            request.args['error'],
            request.args['error_description'],
            pprint.pformat(request.args)
        )
        flash(login_error_message, 'error')
        return redirect(url_for('home'))
    try:
        session['github_token'] = (resp['access_token'], '')
        session['user_data']=github.get('user').data
        github_userid = session['user_data']['login']
        #org_name = os.getenv('GITHUB_ORG')
    except Exception as e:
        session.clear()
        message = 'Unable to login: ' + str(type(e)) + str(e)
        flash(message,'error')
        return redirect(url_for('home'))
    
    try:
        g = Github(resp['access_token'])
        #org = g.get_organization(org_name)
        named_user = g.get_user(github_userid)
        #isMember = org.has_in_members(named_user)
    except Exception as e:
        message = 'Unable to connect to Github with accessToken: ' + resp['access_token'] + " exception info: " + str(type(e)) + str(e)
        session.clear()
        flash(message,'error')
        return redirect(url_for('home'))

    else:
        flash('You were successfully logged in')

    return redirect(url_for('home'))

# Step 9: Here is the part that starts the main job of the app after it has logged in
# and given the appropriate access
@app.route('/replicate', methods=['GET', 'POST'])
def replicate():
    theToken = session.get('github_token')[0]

    g = Github(theToken)
    repo_name = request.form['repo']
    user = g.get_user()
    repo = user.create_repo(repo_name)  

    for file in FILES:
        with open(file) as f:
            filename = f.read()
        repo.create_file(path=file, message='add {}'.format(file), content=filename)
    flash('The repo is created!')
    return redirect(url_for('home'))


if __name__ == "__main__":
    # A workaround after facing at=error code=H10 on Heroku. Because the port is
    # dynamically set in Heroku
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)



