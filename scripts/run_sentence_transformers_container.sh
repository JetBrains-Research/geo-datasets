GPU_ARGS=()

if [[ "${1:-}" == "--gpu" ]]; then
  GPU_ARGS=(--gpus all)
fi

docker run \
  -d \
  "${GPU_ARGS[@]}" \
  --name pubk-embeddings \
  --restart always \
  -v  ./resources/docker/sentence_transformers/config.properties:/config/config.properties:ro \
  -v ~/.geo-datasets/logs:/logs \
  -v ~/.geo-datasets/sentence-transformers:/sentence-transformers \
  -v ~/.geo-datasets/nltk_data:/home/user/nltk_data \
  -p 5001:5001 \
  --health-cmd='python3 -c "import urllib.request; urllib.request.urlopen(\"http://localhost:5001\")"' \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=60s \
  biolabs/sentence-transformers \
  /bin/bash -c '/bin/bash ~/pubk/scripts/nlp.sh \
   && gunicorn --bind 0.0.0.0:5001 --workers 1 --threads 1 --worker-class=gthread \
       --limit-request-line 0 --timeout=600 \
       --log-level=info --log-file=/logs/sentence_transformer_gunicorn.log \
       "pysrc.endpoints.embeddings.sentence_transformer.sentence_transformer_app:get_app()"'
