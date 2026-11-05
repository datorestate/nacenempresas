FROM apify/actor-python:3.12
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt "apify>=2.0"
COPY nacenempresas ./nacenempresas
COPY config ./config
COPY apify/src ./src
ENV RC_DATA_DIR=/tmp/rc-data
CMD ["python", "-m", "src.main"]
