#!/usr/bin/env python 

import json
import urllib
import urllib2
import gtk

class StravaUpload:
    def __init__(self, parent = None, pytrainer_main = None, conf_dir = None, options = None):
        self.pytrainer_main = pytrainer_main
        self.conf_dir = conf_dir

        self.login_url = "https://www.strava.com/api/v2/authentication/login"
        self.upload_url = "http://www.strava.com/api/v2/upload"
        self.strava_token = "%s/.strava_token" % self.conf_dir

        self.email = options['stravauploademail']
        self.password = options['stravauploadpassword']

    def get_web_data(self, url, values):
        data = urllib.urlencode(values)
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req)
        return json.loads(response.read())

    def login_token(self):
        token = None
        try:
            with open(self.strava_token) as f:
                token = f.readline()
        except:
            pass
        if token is None or token.strip() == '' :
            values = { 'email' : self.email, 'password' : self.password }
            result = self.get_web_data(self.login_url, values)
            token = result['token']
            try:
                with open(self.strava_token, 'w') as f:
                    f.write(token)
            except:
                # didn't write token but that's ok, get another next time...
                pass
        return token 

    def upload(self, token, gpx_file):
        gpx = None
        upload_id = 0
        try:
            with open(gpx_file) as f:
                gpx = f.read()
        except:
            pass
        if gpx is not None and gpx.strip() != '':
            values = { 'token': token, 'type': 'gpx', 'data': gpx }
            result = self.get_web_data(self.upload_url, values)
            upload_id = result['upload_id']
        return upload_id

    def run(self, id, activity = None):
        log = "Strava Upload "
        gpx_file = "%s/gpx/%s.gpx" % (self.conf_dir, id)
        try:
            user_token = self.login_token();
            if user_token is not None:
                upload_id = self.upload(user_token, gpx_file)
                if upload_id > 0:
                    log = log + "success (id: %s)!" % upload_id
                else:
                    log = log + "failed to upload!"
        except (ValueError, KeyError), e:
            log = log + ("JSON error: %s.  Username and password correct?" % e)
        except Exception, e:
            log = log + "failed! %s" % e
        md = gtk.MessageDialog(self.pytrainer_main.windowmain.window1, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, log)
        md.set_title(_("Strave Upload"))
        md.set_modal(False)
        md.run()
        md.destroy()
