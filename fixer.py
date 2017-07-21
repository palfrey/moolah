from __future__ import print_function
from requests_oauthlib import OAuth1Session
import requests
import yaml
from flask import (Flask, render_template, url_for,
                   request, session, redirect, flash)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
from models import build_models
from datetime import datetime
import math
import logging
import os
import json


def enable_request_logging():
    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client
    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


# enable_request_logging()

app = Flask(__name__)
if "DYNO" in os.environ:
    app.logger.info(
        "Found DYNO environment variable, so assuming we're in Heroku")
    config = {
        "app": {
            "database_uri": os.environ["DATABASE_URL"]
        },
        "splitwise": {
            "client_id": os.environ["CLIENT_ID"],
            "client_secret": os.environ["CLIENT_SECRET"]
        },
        "flask": {
            "secret_key": os.environ["FLASK_ENCRYPTION_KEY"]
        }
    }
else:
    config = yaml.safe_load(open('config.yaml', 'r'))


@app.before_first_request
def initial_setup():
    with app.app_context():
        upgrade()


@app.before_request
def make_session_permanent():
    session.permanent = True


app.secret_key = config["flask"]["secret_key"]
app.config['SQLALCHEMY_DATABASE_URI'] = config["app"]["database_uri"]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
models = build_models(db)
User = models["User"]
Expense = models["Expense"]


def get_existing():
    if "splitwise_id" in session:
        existing = User.query.filter_by(
            splitwise_id=session["splitwise_id"]).first()
        if existing is None:
            del session["splitwise_id"]
            return None
        else:
            return existing
    return None


def get_default_currency(api):
    currency = api.get(
        "https://secure.splitwise.com/api/v3.0/get_current_user")
    currency.raise_for_status()
    currency = currency.json()["user"]["default_currency"]
    if currency is None:
        currency = "GBP"
    return currency


def wrong_expenses(api, existing, currency):
    expenses = api.get(existing.expenses_url())
    expenses.raise_for_status()
    wrong = []
    for expense in expenses.json()["expenses"]:
        if expense["comments_count"] > 0:
            existing = Expense.query.filter_by(id=expense["id"]).first()
            when = datetime.strptime(
                expense["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
            if existing is None or when > existing.last_update:
                print("get comment", expense["id"])
                comments = Expense.get_comments(api, expense["id"])
                info = None
                if existing is None:
                    existing = Expense(
                        id=expense["id"],
                        last_update=when,
                        original_currency=expense["currency_code"],
                        original_value=expense["cost"])
                    db.session.add(existing)
                else:
                    existing.last_update = when
                for comment in comments[::-1]:
                    if comment["deleted_at"] is not None:
                        continue
                    try:
                        info = json.loads(comment["content"])
                    except ValueError:
                        pass
                if info is not None:
                    if info["updated_for"] != expense["id"]:
                        raise Exception
                    existing.original_currency = info["original_currency"]
                    existing.original_value = info["original_value"]

                db.session.commit()
        if expense['currency_code'] != currency:
            when = datetime.strptime(
                expense["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            original = float(expense["cost"])
            rate = requests.get(
                "http://api.fixer.io/%s?base=%s&symbols=%s" %
                (when.strftime("%Y-%m-%d"),
                    currency,
                    expense['currency_code']))
            rate.raise_for_status()
            rate = rate.json()

            if expense['currency_code'] not in rate["rates"]:
                convert = None
                converted = "Can't convert %s" % expense['currency_code']
            else:
                convert = rate["rates"][expense['currency_code']]
                converted = original/convert
                # round to nearest 1/100th of unit
                converted = round(converted, 2)
            wrong.append({
                "id": expense["id"],
                "description": expense["description"],
                "when": when,
                "from_value": expense["cost"],
                "from_currency": expense['currency_code'],
                "to_currency": currency,
                "to_value": converted,
                "rate": convert})
    return wrong


@app.route("/")
def index():
    existing = get_existing()
    if existing is not None:
        api = existing.authed_api(config["splitwise"]["client_id"],
                                  config["splitwise"]["client_secret"])
        currency = get_default_currency(api)
        wrong = wrong_expenses(api, existing, currency)
        return render_template('index.html',
                               data=existing, wrong=wrong,
                               currency=currency, **config)
    else:
        return render_template('index.html', **config)


@app.route("/oauth/request")
def oauth_request():
    request_token_url = \
        'https://secure.splitwise.com/api/v3.0/get_request_token'

    oauth = OAuth1Session(config["splitwise"]["client_id"],
                          client_secret=config["splitwise"]["client_secret"])
    fetch_response = oauth.fetch_request_token(request_token_url)
    resource_owner_key = fetch_response.get('oauth_token')
    resource_owner_secret = fetch_response.get('oauth_token_secret')
    existing = None
    if "splitwise_id" in session:
        existing = User.query.filter_by(
            splitwise_id=session["splitwise_id"]).first()
        if existing is not None:
            existing.resource_owner_key = resource_owner_key
            existing.resource_owner_secret = resource_owner_secret
    if existing is None:
        existing = User(resource_owner_key, resource_owner_secret)
        db.session.add(existing)
    db.session.commit()

    base_authorization_url = 'https://secure.splitwise.com/authorize'
    authorization_url = oauth.authorization_url(base_authorization_url)
    return redirect(authorization_url)


@app.route("/oauth/response", methods=["GET"])
def oauth_response():
    verifier = request.args['oauth_verifier']
    oauth_token = request.args['oauth_token']
    existing = User.query.filter_by(
            resource_owner_key=oauth_token).first()
    access_token_url = 'https://secure.splitwise.com/api/v3.0/get_access_token'

    client_key = config["splitwise"]["client_id"]
    client_secret = config["splitwise"]["client_secret"]

    oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          resource_owner_key=existing.resource_owner_key,
                          resource_owner_secret=existing.resource_owner_secret,
                          verifier=verifier)
    oauth_tokens = oauth.fetch_access_token(access_token_url)
    resource_owner_key = oauth_tokens.get('oauth_token')
    resource_owner_secret = oauth_tokens.get('oauth_token_secret')

    splitwise = OAuth1Session(client_key,
                              client_secret=client_secret,
                              resource_owner_key=resource_owner_key,
                              resource_owner_secret=resource_owner_secret)

    url = 'https://secure.splitwise.com/api/v3.0/test'
    r = splitwise.get(url)
    r.raise_for_status()
    data = r.json()
    other_existing = User.query.filter_by(
            splitwise_id=data["token"]["user_id"]).first()
    if other_existing is not None and existing.id != other_existing.id:
        db.session.delete(existing)
        existing = other_existing
    existing.splitwise_id = data["token"]["user_id"]
    existing.resource_owner_key = resource_owner_key
    existing.resource_owner_secret = resource_owner_secret
    db.session.commit()
    session["splitwise_id"] = existing.splitwise_id
    return redirect(url_for("index"))


def convert_money(value, rate):
    if value is None:
        return None
    return round(float(value)/rate, 2)  # nearest 100th of unit


def update_expense(api, id, currency, rate):
    expense = api.get(
            "https://secure.splitwise.com/api/v3.0/get_expense/%s" % id)
    expense.raise_for_status()
    expense = expense.json()["expense"]
    rate = float(rate)
    new_data = {
        "currency_code": currency,
        "cost": convert_money(expense["cost"], rate)
    }
    expense_obj = Expense.query.filter_by(id=id).first()
    expense_obj.add_comment(api, json.dumps(
        {
            "original_currency": expense["currency_code"],
            "original_value": expense["cost"],
            "updated_for": expense["id"]
        }))
    owed_total = 0
    least_owed = most_owed = None
    for idx, user in enumerate(expense["users"]):
        new_user = {
            "user_id": user["user_id"],
            "paid_share": convert_money(user["paid_share"], rate),
            "owed_share": convert_money(user["owed_share"], rate)
        }
        owed_total += new_user["owed_share"]
        if least_owed is None or \
                new_data["users__array_%d__owed_share" % least_owed] > \
                new_user["owed_share"]:
            least_owed = idx
        if most_owed is None or \
                new_data["users__array_%d__owed_share" % most_owed] < \
                new_user["owed_share"]:
            most_owed = idx
        for key in new_user.keys():
            new_data["users__array_%d__%s" % (idx, key)] = new_user[key]
    if owed_total != new_data["cost"]:
        # need to correct
        difference = owed_total-new_data["cost"]
        if math.fabs(round(difference, 2)) != 0.01:
            # something odd has happened
            raise Exception((difference, math.fabs(difference)))
        if difference > 0:
            new_data["users__array_%d__owed_share" % most_owed] -= difference
        else:
            new_data["users__array_%d__owed_share" % least_owed] -= difference
    update = api.put(
        "https://secure.splitwise.com/api/v3.0/update_expense/%s" % id,
        data=new_data)
    update.raise_for_status()
    update = update.json()
    if "errors" in update and update["errors"] != {}:
        raise Exception(update)


@app.route("/update", methods=["POST"])
def update_expense_req():
    existing = get_existing()
    if existing is not None:
        api = existing.authed_api(
            config["splitwise"]["client_id"],
            config["splitwise"]["client_secret"])
        update_expense(
            api,
            request.form["id"],
            request.form["currency"],
            request.form["rate"])
        flash("Updated expense")
    return redirect(url_for('index'))


def update_all(user):
    api = user.authed_api(
        config["splitwise"]["client_id"],
        config["splitwise"]["client_secret"])
    currency = get_default_currency(api)
    wrong = wrong_expenses(api, user, currency)
    for expense in wrong:
        if expense["rate"] is None:
            continue
        update_expense(api, expense["id"], currency, expense["rate"])
    user.update()


@app.route("/update/all", methods=["POST"])
def update_all_req():
    existing = get_existing()
    if existing is not None:
        update_all(existing)
        flash("Updated all expenses")
    return redirect(url_for('index'))


if __name__ == "__main__":
    users = User.query.all()
    for user in users:
        if user.splitwise_id is None:
            print("No splitwise id for", user)
            continue
        print("Updating", user)
        update_all(user)
    db.session.commit()
