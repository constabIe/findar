from prometheus_client import Counter, Gauge, Histogram

ml_models_total = Counter("ml_models_total", "Total ML models registered")
ml_models_active = Gauge("ml_models_active", "Number of active ML models")
ml_models_failed = Gauge("ml_models_failed", "Number of failed ML models")

ml_model_test_latency_seconds = Histogram(
    "ml_model_test_latency_seconds", "Latency of model test endpoint"
)

ml_model_inference_seconds = Histogram(
    "ml_model_inference_seconds", "Inference time for local model predictions"
)

ml_model_load_seconds = Histogram(
    "ml_model_load_seconds", "Time taken to load model into memory"
)
