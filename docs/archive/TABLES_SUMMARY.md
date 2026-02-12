# Database Tables - Quick Summary

## 🎯 The Answer To Your Question

Those **15 empty tables** (`input_tags`, `inputs`, `latest_metrics`, `metrics`, etc.) are **MLflow tables**.

### What is MLflow?
MLflow is an open-source ML experiment tracking platform that automatically creates these tables for:
- Tracking ML training experiments
- Managing model versions
- Logging metrics and parameters
- Dataset provenance

### Why are they empty?
✅ **This is correct and expected!** They're only used when you actively log ML experiments. Your system currently:
- Uses **pre-trained models** (loaded from pickle files)
- Doesn't need experiment tracking for inference
- Has MLflow ready if you want to train/track models in the future

### Should you worry about them?
❌ **No!** They:
- Use minimal database space
- Don't impact performance
- Are a best practice for ML systems
- Will be useful if you ever retrain models

---

## 📊 Table Breakdown

### GPU Health Monitor Tables (8 tables) - YOURS ✅

All actively used for GPU monitoring:

```
gpu_assets               - GPU inventory (1 row)
gpu_metrics              - Time-series data (630+ rows, updating every 10s)
gpu_health_scores        - Health assessments (6 rows, every 15min)
gpu_features             - ML features (8 rows, every 5min)
gpu_failure_predictions  - Failure forecasts (7 rows, every 5min)
gpu_economic_decisions   - Lifecycle recommendations (5 rows, every 30min)
anomalies                - Detected anomalies (66 rows, every 5min)
gpu_failure_labels       - Training labels (0 rows - no failures yet)
```

### MLflow Tables (15 tables) - EMPTY (Expected) ✅

For ML experiment tracking (not needed for inference):

**Experiment Tracking:**
- experiments, runs, metrics, params, tags, latest_metrics

**Model Registry:**
- registered_models, model_versions, model_version_tags
- registered_model_aliases, registered_model_tags

**Dataset Tracking:**
- datasets, inputs, input_tags, experiment_tags

### Utility Tables (2 tables)
- alembic_version - Database migration tracking

---

## 🎯 Bottom Line

**Total Tables:** 25  
**Your GPU Monitoring Tables:** 8 (all working ✅)  
**MLflow Tables:** 15 (empty by design ✅)  
**Utility Tables:** 2 (system metadata ✅)

**Everything is correct!** The empty MLflow tables are ready for future ML experiment tracking if needed.
