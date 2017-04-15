import datetime
import humanize
from requests_oauthlib import OAuth1Session


def build_models(db):
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        splitwise_id = db.Column(db.Integer)
        splitwise_access_token = db.Column(db.String(40), unique=True)
        resource_owner_key = db.Column(db.String(40), unique=True)
        resource_owner_secret = db.Column(db.String(40), unique=True)
        last_update = db.Column(db.DateTime)

        def __init__(self, resource_owner_key, resource_owner_secret):
            self.resource_owner_key = resource_owner_key
            self.resource_owner_secret = resource_owner_secret

        def pretty_update(self):
            if self.last_update is None:
                return "Never"
            return humanize.naturaltime(
                datetime.datetime.now() - self.last_update)

        def update(self):
            self.last_update = datetime.datetime.now()

        def __repr__(self):
            return '<User %r>' % self.splitwise_id

        def authed_api(self, client_key, client_secret):
            return OAuth1Session(
                client_key,
                client_secret=client_secret,
                resource_owner_key=self.resource_owner_key,
                resource_owner_secret=self.resource_owner_secret)

        def expenses_url(self):
            url = "https://secure.splitwise.com/api/v3.0/get_expenses"
            if self.last_update is None:
                url += "?limit=0"
            else:
                url += "?updated_after=%s" % \
                    self.last_update.strftime("%Y-%m-%d")
            return url

    try:
        User.query.first()
    except:  # Assume that failure means tables not created
        db.create_all()
    return {"User": User}
