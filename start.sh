#!/bin/bash
gunicorn --bind 0.0.0.0:$PORT --worker-class gevent main:app