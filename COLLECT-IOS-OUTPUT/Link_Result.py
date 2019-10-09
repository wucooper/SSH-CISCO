#!/usr/bin/env python


import yaml
from flask import Flask, render_template
import jinja2


DEV_LIST = []

app = Flask(__name__)


@app.route('/')
def load_html():
	global DEV_LIST
	yml_stream = open('./GHD_HA_MONITORING_CUR.yml','r')
	DEV_LIST   = yaml.load(yml_stream)
	yml_stream.close()
	return render_template('Link_HA.html',dev_results = DEV_LIST)




if __name__ == '__main__':


	app.run('0.0.0.0')


