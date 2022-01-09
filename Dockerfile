FROM joyzoursky/python-chromedriver:3.9-selenium

WORKDIR /app

COPY setup.py /app/setup.py
COPY main.py /app/
COPY wardreport /app/wardreport/
RUN python3 setup.py install

ENTRYPOINT [ "python3", "/app/main.py"]
