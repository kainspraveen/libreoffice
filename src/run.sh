#!/bin/bash
/usr/bin/soffice --headless --nologo --nofirststartwizard --accept="socket,host=127.0.0.1,port=2002;urp;" &

/usr/bin/python -m uvicorn app:app --host 0.0.0.0 --port 5000