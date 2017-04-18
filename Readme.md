Moolah
======
[![Build Status](https://travis-ci.org/palfrey/moolah.svg?branch=master)](https://travis-ci.org/palfrey/moolah)

Moolah is a tool for converting money in your non-default currency in your [Splitwise](https://splitwise.com/)
account into your default currency, using the rates for that day from [fixer.io](http://fixer.io/).

Local Setup
-----------
1. Copy `config.yaml.example` to `config.yaml` and fill in the values there as we go through the later steps
2. Register app at https://secure.splitwise.com/oauth_clients and get the OAuth Client/Secret for `config.yaml`
    * Callback URL should be "&lt;host&gt;/oauth/response" (http://localhost:5000/oauth/response for local setup)
3. If you've already got [Bower](https://bower.io/) installed, just run `bower install`. Otherwise, install [Node.js](https://nodejs.org/en/) and run `npm install`, which will install and run Bower.
4. `pip install -r requirements.txt` (preferably within a [Virtualenv](https://virtualenv.pypa.io/en/stable/) because that's just sensible)
5. `./debug-run.sh`

You've now got a running version of the app at http://localhost:5000. Running `python fixer.py` will synchronise all registered users.

Heroku Setup
------------

There's a running instance of this at https://moolah-heroku.herokuapp.com/ but here's how I did that.

1. Get a [Heroku](https://www.heroku.com/) account. Free ones work fine.
2. Install the [Heroku toolbelt](https://toolbelt.heroku.com/)
3. Goto your [dashboard](https://dashboard.heroku.com/apps/) and make a new app. Mine was called "moolah-heroku" but you'll need to use another name for yours, and replace anywhere I use that.
4. `heroku git:remote --app moolah-heroku` to make it possible to push to deploy to your new app.
5. We're using multiple buildpacks, both the Python (backend) and Node.js (assets). You'll need to do the following:
    1. `heroku buildpacks:add --index 1 heroku/nodejs`
    2. `heroku buildpacks:add --index 2 heroku/python`
    3. `heroku buildpacks` should now say (and if it doesn't, read [the docs](https://devcenter.heroku.com/articles/using-multiple-buildpacks-for-an-app))
        1. heroku/nodejs
            2. heroku/python
6. Add the [PostgreSQL addon](https://elements.heroku.com/addons/heroku-postgresql)
7. Go into the settings for your app and set the following config variables:
   * CLIENT_ID/CLIENT_SECRET - Splitwise app configured as per above, but with your Heroku URL, not localhost
   * FLASK_ENCRYPTION_KEY - Something secret for Flask to use for [cookie encryption](http://flask.pocoo.org/docs/0.11/quickstart/#sessions)
8. [`git push heroku master`](https://devcenter.heroku.com/articles/git#deploying-code)
8. At this point, goto your Heroku URL and check everything works. You might have an error page the first time you load it due to clashes between multiple workers all trying to configure the DB. Just refresh and it should fix itself.
9. Add the [Scheduler addon](https://elements.heroku.com/addons/scheduler) and configure the update command (`python fixer.py`) to run every so often.
