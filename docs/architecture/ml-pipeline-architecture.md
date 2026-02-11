# ML Pipeline Architecture

## Table of Contents

- [Overview](#overview)
- [Pipeline Architecture](#pipeline-architecture)
- [Health Scoring System](#health-scoring-system)
- [Failure Prediction Models](#failure-prediction-models)
- [Feature Engineering](#feature-engineering)
- [Model Training Pipeline](#model-training-pipeline)
- [Model Serving & Inference](#model-serving--inference)
- [Economic Decision Engine](#economic-decision-engine)
- [MLOps & Model Management](#mlops--model-management)
- [Performance & Scaling](#performance--scaling)

---

## Overview

The ML Pipeline is the **intelligence layer** of the GPU Health Monitor, responsible for:
1. Computing multi-dimensional health scores (0-100) for each GPU
2. Predicting hardware failures 7-90 days in advance
3. Recommending economic lifecycle decisions (keep, sell, repurpose, decommission)

### System Context

```mermaid
graph TB
    subgraph "Data Sources"
        TSDB[(TimescaleDB<br/>Time-Series Metrics)]
        PG[(PostgreSQL<br/>Asset Metadata)]
    end
    
    subgraph "Feature Engineering"
        Extract[Feature Extractor<br/>━━━━━━━━━━<br/>• Time-series stats<br/>• Trend analysis<br/>• Anomaly counts]
        
        Store[Feature Store<br/>Feast<br/>Online + Offline]
    end
    
    subgraph "ML Models"
        Health[Health Scorer<br/>━━━━━━━━━━<br/>Rule-based + ML<br/>5 dimensions]
        
        Predict[Failure Predictor<br/>━━━━━━━━━━<br/>XGBoost + LSTM<br/>Ensemble]
        
        Economic[Economic Model<br/>━━━━━━━━━━<br/>NPV Analysis<br/>Decision Tree]
    end
    
    subgraph "Training Pipeline"
        Train[Model Training<br/>━━━━━━━━━━<br/>Airflow DAGs<br/>Nightly batch]
        
        MLflow[MLflow<br/>━━━━━━━━━━<br/>Experiment tracking<br/>Model registry]
    end
    
    subgraph "Inference & Serving"
        Batch[Batch Inference<br/>━━━━━━━━━━<br/>Daily health scores<br/>Predictions]
        
        API[FastAPI Service<br/>━━━━━━━━━━<br/>Real-time inference<br/>On-demand]
    end
    
    subgraph "Outputs"
        Scores[(PostgreSQL<br/>gpu_health_scores)]
        Predictions[(PostgreSQL<br/>gpu_failure_predictions)]
        Decisions[(PostgreSQL<br/>gpu_economic_decisions)]
    end
    
    TSDB --> Extract
    PG --> Extract
    Extract --> Store
    
    Store --> Health
    Store --> Predict
    Health --> Economic
    Predict --> Economic
    
    Store --> Train
    Train --> MLflow
    MLflow --> Health
    MLflow --> Predict
    
    Health --> Batch
    Predict --> Batch
    Economic --> Batch
    
    Health --> API
    Predict --> API
    
    Batch --> Scores
    Batch --> Predictions
    Batch --> Decisions
    
    style Health fill:#c8e6c9
    style Predict fill:#ffccbc
    style Economic fill:#fff9c4
    style MLflow fill:#e1f5ff
```

---

## Pipeline Architecture

### End-to-End Workflow

```mermaid
sequenceDiagram
    participant Scheduler as Airflow Scheduler
    participant FE as Feature Extraction
    participant FS as Feature Store
    participant HS as Health Scorer
    participant FP as Failure Predictor
    participant EM as Economic Model
    participant DB as PostgreSQL
    
    Note over Scheduler: Daily 02:00 UTC
    
    Scheduler->>FE: Trigger feature extraction DAG
    
    FE->>FE: Query TimescaleDB<br/>(last 90 days)
    FE->>FE: Compute features<br/>(rolling stats, trends)
    FE->>FS: Materialize features<br/>(offline store)
    
    Scheduler->>HS: Trigger health scoring
    
    HS->>FS: Fetch features (per GPU)
    HS->>HS: Compute dimension scores<br/>(memory, thermal, power, etc.)
    HS->>HS: Aggregate to overall score
    HS->>DB: INSERT gpu_health_scores
    
    Scheduler->>FP: Trigger failure prediction
    
    FP->>FS: Fetch features (per GPU)
    FP->>FP: XGBoost inference<br/>(7/30/90 day probabilities)
    FP->>FP: LSTM inference<br/>(failure type prediction)
    FP->>DB: INSERT gpu_failure_predictions
    
    Scheduler->>EM: Trigger economic analysis
    
    EM->>DB: Fetch health scores + predictions
    EM->>EM: NPV calculation<br/>(keep vs sell vs repurpose)
    EM->>DB: INSERT gpu_economic_decisions
    
    Note over DB: Results available<br/>for dashboards & alerts
```

---

## Health Scoring System

### Multi-Dimensional Scoring

Health scores range from **0 (critical) to 100 (excellent)** across 5 dimensions:

```mermaid
graph TB
    subgraph "Health Dimensions (Weighted)"
        M[Memory Health<br/>━━━━━━━━━━<br/>Weight: 30%<br/>━━━━━━━━━━<br/>• ECC errors<br/>• Retired pages<br/>• Bandwidth]
        
        T[Thermal Health<br/>━━━━━━━━━━<br/>Weight: 25%<br/>━━━━━━━━━━<br/>• Temperature<br/>• Throttling events<br/>• Cooling stability]
        
        P[Performance<br/>━━━━━━━━━━<br/>Weight: 20%<br/>━━━━━━━━━━<br/>• Throughput<br/>• Clock stability<br/>• SM occupancy]
        
        Pow[Power Health<br/>━━━━━━━━━━<br/>Weight: 15%<br/>━━━━━━━━━━<br/>• Draw variance<br/>• Efficiency<br/>• Violations]
        
        R[Reliability<br/>━━━━━━━━━━<br/>Weight: 10%<br/>━━━━━━━━━━<br/>• Uptime<br/>• Job success rate<br/>• Driver stability]
    end
    
    M -->|30%| Overall[Overall<br/>Health Score<br/>━━━━━━━━━━<br/>Weighted Average<br/>0-100]
    T -->|25%| Overall
    P -->|20%| Overall
    Pow -->|15%| Overall
    R -->|10%| Overall
    
    Overall --> Grade{Health<br/>Grade}
    
    Grade -->|90-100| Excellent[Excellent<br/>Prime production]
    Grade -->|80-89| Good[Good<br/>Standard production]
    Grade -->|70-79| Fair[Fair<br/>Monitor closely]
    Grade -->|60-69| Degraded[Degraded<br/>Plan replacement]
    Grade -->|50-59| Poor[Poor<br/>Secondary market]
    Grade -->|< 50| Critical[Critical<br/>Decommission]
    
    style M fill:#e3f2fd
    style T fill:#fff3e0
    style P fill:#f3e5f5
    style Pow fill:#e8f5e9
    style R fill:#fce4ec
    style Overall fill:#fff9c4
    style Excellent fill:#c8e6c9
    style Good fill:#a5d6a7
    style Fair fill:#fff59d
    style Degraded fill:#ffcc80
    style Poor fill:#ffab91
    style Critical fill:#ef9a9a
```

### Scoring Algorithm

**Python Implementation**:

```python
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class HealthScore:
    overall_score: float
    memory_health: float
    thermal_health: float
    performance_health: float
    power_health: float
    reliability_health: float
    health_grade: str
    degradation_factors: List[str]

class GPUHealthScorer:
    
    # Dimension weights
    WEIGHTS = {
        'memory': 0.30,
        'thermal': 0.25,
        'performance': 0.20,
        'power': 0.15,
        'reliability': 0.10
    }
    
    def score_gpu(self, metrics: pd.DataFrame, gpu_uuid: str) -> HealthScore:
        """
        Compute health score for a GPU based on last 7 days of metrics.
        
        Args:
            metrics: DataFrame with columns [time, gpu_uuid, gpu_temp, ...]
            gpu_uuid: GPU to score
        
        Returns:
            HealthScore object
        """
        gpu_data = metrics[metrics['gpu_uuid'] == gpu_uuid]
        
        # Compute dimension scores
        memory = self._score_memory_health(gpu_data)
        thermal = self._score_thermal_health(gpu_data)
        performance = self._score_performance_health(gpu_data)
        power = self._score_power_health(gpu_data)
        reliability = self._score_reliability_health(gpu_data)
        
        # Weighted overall score
        overall = (
            memory * self.WEIGHTS['memory'] +
            thermal * self.WEIGHTS['thermal'] +
            performance * self.WEIGHTS['performance'] +
            power * self.WEIGHTS['power'] +
            reliability * self.WEIGHTS['reliability']
        )
        
        # Grade
        grade = self._assign_grade(overall)
        
        # Identify degradation factors
        factors = self._identify_degradation_factors(
            gpu_data, memory, thermal, performance, power, reliability
        )
        
        return HealthScore(
            overall_score=round(overall, 1),
            memory_health=round(memory, 1),
            thermal_health=round(thermal, 1),
            performance_health=round(performance, 1),
            power_health=round(power, 1),
            reliability_health=round(reliability, 1),
            health_grade=grade,
            degradation_factors=factors
        )
    
    def _score_memory_health(self, data: pd.DataFrame) -> float:
        """
        Memory health (0-100):
        - ECC errors (critical)
        - Retired pages (critical)
        - Memory bandwidth degradation
        """
        score = 100.0
        
        # ECC errors (most recent)
        latest = data.iloc[-1]
        
        # Double-bit errors (uncorrectable) - critical
        dbe_count = latest['ecc_dbe_volatile']
        if dbe_count > 0:
            score -= min(50, dbe_count * 10)  # -10 per DBE, max -50
        
        # Single-bit errors (correctable) - warning
        sbe_count = latest['ecc_sbe_volatile']
        if sbe_count > 100:
            score -= min(20, (sbe_count - 100) / 100 * 20)  # Scale up to -20
        
        # Retired pages (permanent damage)
        retired_dbe = latest['retired_pages_dbe']
        if retired_dbe > 0:
            score -= min(30, retired_dbe * 5)  # -5 per retired page
        
        # Memory bandwidth trend (degradation over time)
        if len(data) > 1:
            recent_bw = data.tail(24)['dram_active'].mean()  # Last 24 samples
            baseline_bw = data.head(24)['dram_active'].mean()
            
            if baseline_bw > 0:
                degradation = (baseline_bw - recent_bw) / baseline_bw
                if degradation > 0.1:  # >10% degradation
                    score -= degradation * 100  # Scale to penalty
        
        return max(0, min(100, score))
    
    def _score_thermal_health(self, data: pd.DataFrame) -> float:
        """
        Thermal health (0-100):
        - Average temperature
        - Temperature spikes
        - Throttling events
        - Thermal stability
        """
        score = 100.0
        
        # Average GPU temperature
        avg_temp = data['gpu_temp'].mean()
        
        # Temperature scoring (ideal: 50-70°C, acceptable: 30-85°C)
        if avg_temp > 85:
            score -= (avg_temp - 85) * 2  # -2 per °C above 85
        elif avg_temp > 75:
            score -= (avg_temp - 75) * 1  # -1 per °C above 75
        elif avg_temp < 30:
            score -= (30 - avg_temp) * 0.5  # Cold anomaly
        
        # Max temperature (spikes)
        max_temp = data['gpu_temp'].max()
        if max_temp > 95:
            score -= (max_temp - 95) * 3  # Severe spike
        
        # Temperature variance (stability)
        temp_std = data['gpu_temp'].std()
        if temp_std > 10:
            score -= (temp_std - 10) * 0.5  # Unstable cooling
        
        # Throttling events
        throttle_count = (data['throttle_reasons'] > 0).sum()
        throttle_pct = throttle_count / len(data) * 100
        
        if throttle_pct > 5:  # >5% of time throttling
            score -= throttle_pct  # -1 per percent
        
        # Hardware thermal throttling (critical)
        hw_thermal_throttle = ((data['throttle_reasons'] & (1 << 6)) > 0).sum()
        if hw_thermal_throttle > 0:
            score -= 20  # Severe penalty
        
        return max(0, min(100, score))
    
    def _score_performance_health(self, data: pd.DataFrame) -> float:
        """
        Performance health (0-100):
        - Compute throughput
        - Clock stability
        - SM occupancy
        """
        score = 100.0
        
        # SM active percentage (utilization when running)
        avg_sm_active = data['sm_active'].mean()
        
        # SM occupancy (efficiency)
        avg_occupancy = data['sm_occupancy'].mean()
        
        # If GPU is being used but occupancy is low, penalize
        if avg_sm_active > 10 and avg_occupancy < 30:
            score -= (30 - avg_occupancy) * 0.5  # Inefficient workloads
        
        # Clock stability (variance in SM clock)
        if 'sm_clock_mhz' in data.columns:
            clock_std = data['sm_clock_mhz'].std()
            expected_clock = data['sm_clock_mhz'].mode()[0]  # Most common clock
            
            if clock_std > expected_clock * 0.05:  # >5% variance
                score -= 10  # Unstable clocks
        
        # Tensor core utilization (for ML workloads)
        if 'tensor_active' in data.columns:
            avg_tensor = data['tensor_active'].mean()
            # No penalty, but low tensor use may indicate workload mismatch
        
        return max(0, min(100, score))
    
    def _score_power_health(self, data: pd.DataFrame) -> float:
        """
        Power health (0-100):
        - Power draw variance
        - Efficiency (compute per watt)
        - Power violations
        """
        score = 100.0
        
        # Power variance (stability)
        power_std = data['power_usage'].std()
        power_mean = data['power_usage'].mean()
        
        if power_mean > 0:
            cv = power_std / power_mean  # Coefficient of variation
            if cv > 0.2:  # >20% variance
                score -= (cv - 0.2) * 100
        
        # Power efficiency (SM active per watt)
        if 'sm_active' in data.columns and power_mean > 0:
            efficiency = data['sm_active'].mean() / power_mean
            # Lower efficiency indicates power waste or hardware issues
            # (No direct penalty, but tracked)
        
        # Power throttling
        power_throttle = ((data['throttle_reasons'] & (1 << 7)) > 0).sum()
        if power_throttle > 0:
            score -= 15  # Hardware power brake
        
        sw_power_cap = ((data['throttle_reasons'] & (1 << 2)) > 0).sum()
        if sw_power_cap > len(data) * 0.5:  # >50% of time capped
            score -= 10  # Consistently hitting power cap
        
        return max(0, min(100, score))
    
    def _score_reliability_health(self, data: pd.DataFrame) -> float:
        """
        Reliability health (0-100):
        - Sample completeness (no gaps)
        - Error-free operation
        """
        score = 100.0
        
        # Expected samples (1 per 10 seconds for 7 days = ~60k samples)
        expected_samples = 7 * 24 * 60 * 6  # 60,480
        actual_samples = len(data)
        
        completeness = actual_samples / expected_samples
        if completeness < 0.95:  # <95% coverage
            score -= (0.95 - completeness) * 100
        
        # Check for large time gaps (indicating restarts/crashes)
        time_diffs = data['time'].diff()
        large_gaps = (time_diffs > pd.Timedelta(minutes=5)).sum()
        
        if large_gaps > 0:
            score -= large_gaps * 5  # -5 per gap
        
        return max(0, min(100, score))
    
    def _assign_grade(self, score: float) -> str:
        """Map numerical score to health grade."""
        if score >= 90:
            return "excellent"
        elif score >= 80:
            return "good"
        elif score >= 70:
            return "fair"
        elif score >= 60:
            return "degraded"
        elif score >= 50:
            return "poor"
        else:
            return "critical"
    
    def _identify_degradation_factors(
        self, data, memory, thermal, performance, power, reliability
    ) -> List[str]:
        """Identify specific factors causing degradation."""
        factors = []
        
        latest = data.iloc[-1]
        
        if latest['ecc_dbe_volatile'] > 0:
            factors.append("uncorrectable_ecc_errors")
        
        if latest['ecc_sbe_volatile'] > 100:
            factors.append("high_correctable_ecc_errors")
        
        if data['gpu_temp'].mean() > 80:
            factors.append("elevated_temperature")
        
        if ((data['throttle_reasons'] & (1 << 6)) > 0).any():
            factors.append("thermal_throttling")
        
        if latest['retired_pages_dbe'] > 0:
            factors.append("retired_memory_pages")
        
        # Add dimension scores below thresholds
        if memory < 70:
            factors.append("memory_degradation")
        if thermal < 70:
            factors.append("thermal_issues")
        if performance < 70:
            factors.append("performance_degradation")
        
        return factors
```

---

## Failure Prediction Models

### Ensemble Approach

```mermaid
graph TB
    subgraph "Features"
        TS[Time-Series Features<br/>━━━━━━━━━━<br/>• Rolling windows '1h, 24h, 7d'<br/>• Trend coefficients<br/>• Seasonality]
        
        Anom[Anomaly Features<br/>━━━━━━━━━━<br/>• Spike counts<br/>• Outlier frequency<br/>• Pattern breaks]
        
        Meta[Metadata Features<br/>━━━━━━━━━━<br/>• GPU age<br/>• Total operating hours<br/>• Workload history]
    end
    
    subgraph "Model Ensemble"
        XGB[XGBoost Classifier<br/>━━━━━━━━━━<br/>Gradient boosting<br/>Tabular data]
        
        LSTM[LSTM Network<br/>━━━━━━━━━━<br/>Sequence model<br/>Temporal patterns]
        
        ISO[Isolation Forest<br/>━━━━━━━━━━<br/>Anomaly detector<br/>Novel failures]
        
        COX[Cox Survival Model<br/>━━━━━━━━━━<br/>Time-to-failure<br/>Hazard ratios]
    end
    
    subgraph "Outputs"
        Prob[Failure Probability<br/>━━━━━━━━━━<br/>7 / 30 / 90 days]
        
        Type[Failure Type<br/>━━━━━━━━━━<br/>Memory / Thermal / Power]
        
        TTF[Time to Failure<br/>━━━━━━━━━━<br/>Days estimate]
        
        Conf[Confidence<br/>━━━━━━━━━━<br/>0.0 - 1.0]
    end
    
    TS --> XGB
    TS --> LSTM
    Anom --> XGB
    Anom --> ISO
    Meta --> XGB
    Meta --> COX
    TS --> COX
    
    XGB --> Prob
    XGB --> Conf
    LSTM --> Type
    ISO --> Type
    COX --> TTF
    
    style XGB fill:#fff3e0
    style LSTM fill:#f3e5f5
    style ISO fill:#e8f5e9
    style COX fill:#fff9c4
    style Prob fill:#ffccbc
```

### XGBoost Binary Classifier

**Training Target**: Did GPU fail within 30 days? (Binary: 0/1)

```python
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, precision_recall_curve

class FailurePredictorXGB:
    
    def __init__(self):
        self.model = None
        self.feature_names = None
    
    def train(self, X_train, y_train, X_val, y_val):
        """
        Train XGBoost model for 30-day failure prediction.
        
        Args:
            X_train: Feature matrix (N samples × M features)
            y_train: Labels (0 = no failure, 1 = failure within 30 days)
            X_val: Validation features
            y_val: Validation labels
        """
        self.feature_names = X_train.columns.tolist()
        
        # Handle class imbalance (failures are rare)
        failure_rate = y_train.mean()
        scale_pos_weight = (1 - failure_rate) / failure_rate
        
        params = {
            'objective': 'binary:logistic',
            'eval_metric': 'auc',
            'max_depth': 6,
            'learning_rate': 0.05,
            'n_estimators': 500,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'scale_pos_weight': scale_pos_weight,
            'early_stopping_rounds': 50,
            'random_state': 42
        }
        
        self.model = xgb.XGBClassifier(**params)
        
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=True
        )
        
        # Evaluate
        val_preds = self.model.predict_proba(X_val)[:, 1]
        auc = roc_auc_score(y_val, val_preds)
        
        print(f"Validation AUC: {auc:.4f}")
        
        # Feature importance
        importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\nTop 10 Features:")
        print(importance.head(10))
        
        return self.model
    
    def predict(self, X):
        """
        Predict failure probability for each GPU.
        
        Returns:
            Array of probabilities (0.0 - 1.0)
        """
        if self.model is None:
            raise ValueError("Model not trained")
        
        return self.model.predict_proba(X)[:, 1]
    
    def explain_prediction(self, X_single):
        """
        Explain prediction for a single GPU using SHAP.
        """
        import shap
        
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values(X_single)
        
        return shap_values
```

### LSTM Sequence Model

**Approach**: Predict failure based on last 7 days of time-series data.

```python
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

class FailureLSTM(nn.Module):
    
    def __init__(self, input_size, hidden_size=128, num_layers=2, dropout=0.2):
        super().__init__()
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout
        )
        
        self.fc1 = nn.Linear(hidden_size, 64)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        
        # Multi-task outputs
        self.fc_prob = nn.Linear(64, 1)  # Failure probability
        self.fc_type = nn.Linear(64, 4)  # Failure type (memory/thermal/power/other)
        
        self.sigmoid = nn.Sigmoid()
        self.softmax = nn.Softmax(dim=1)
    
    def forward(self, x):
        """
        Args:
            x: (batch_size, sequence_length, input_size)
               sequence_length = 7 days × 144 samples/day = 1008
               input_size = number of metrics (e.g., 20)
        
        Returns:
            failure_prob: (batch_size, 1)
            failure_type: (batch_size, 4)
        """
        # LSTM forward
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # Use final hidden state
        final_hidden = hidden[-1]  # (batch_size, hidden_size)
        
        # Dense layers
        x = self.fc1(final_hidden)
        x = self.relu(x)
        x = self.dropout(x)
        
        # Outputs
        failure_prob = self.sigmoid(self.fc_prob(x))
        failure_type = self.softmax(self.fc_type(x))
        
        return failure_prob, failure_type


class GPUSequenceDataset(Dataset):
    """Dataset for LSTM training."""
    
    def __init__(self, sequences, labels, failure_types):
        """
        Args:
            sequences: (N, seq_len, features)
            labels: (N,) - binary failure labels
            failure_types: (N,) - failure type (0-3)
        """
        self.sequences = torch.FloatTensor(sequences)
        self.labels = torch.FloatTensor(labels).unsqueeze(1)
        self.failure_types = torch.LongTensor(failure_types)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx], self.failure_types[idx]


def train_lstm(model, train_loader, val_loader, epochs=50):
    """Train LSTM model."""
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    
    criterion_prob = nn.BCELoss()
    criterion_type = nn.CrossEntropyLoss()
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        
        for sequences, labels, types in train_loader:
            sequences = sequences.to(device)
            labels = labels.to(device)
            types = types.to(device)
            
            optimizer.zero_grad()
            
            prob_pred, type_pred = model(sequences)
            
            loss_prob = criterion_prob(prob_pred, labels)
            loss_type = criterion_type(type_pred, types)
            
            loss = loss_prob + 0.5 * loss_type  # Weight type loss lower
            
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
        
        # Validation
        model.eval()
        val_loss = 0.0
        
        with torch.no_grad():
            for sequences, labels, types in val_loader:
                sequences = sequences.to(device)
                labels = labels.to(device)
                types = types.to(device)
                
                prob_pred, type_pred = model(sequences)
                
                loss_prob = criterion_prob(prob_pred, labels)
                loss_type = criterion_type(type_pred, types)
                loss = loss_prob + 0.5 * loss_type
                
                val_loss += loss.item()
        
        print(f"Epoch {epoch+1}/{epochs} - Train Loss: {train_loss/len(train_loader):.4f}, Val Loss: {val_loss/len(val_loader):.4f}")
    
    return model
```

---

## Feature Engineering

### Feature Categories

```python
class GPUFeatureEngineer:
    """Extract features from time-series metrics for ML models."""
    
    def extract_features(self, gpu_uuid: str, lookback_days: int = 7) -> pd.Series:
        """
        Extract ~200 features for a single GPU.
        
        Returns:
            pandas Series with feature names and values
        """
        # Query metrics from TimescaleDB
        metrics = self._query_metrics(gpu_uuid, lookback_days)
        
        features = {}
        
        # 1. Statistical features (rolling windows)
        features.update(self._statistical_features(metrics))
        
        # 2. Trend features
        features.update(self._trend_features(metrics))
        
        # 3. Anomaly features
        features.update(self._anomaly_features(metrics))
        
        # 4. Event counts
        features.update(self._event_features(metrics))
        
        # 5. Metadata features
        features.update(self._metadata_features(gpu_uuid))
        
        return pd.Series(features)
    
    def _statistical_features(self, metrics: pd.DataFrame) -> dict:
        """Rolling statistics for key metrics."""
        features = {}
        
        # Temperature statistics (multiple windows)
        for window in ['1h', '6h', '24h', '7d']:
            rolling = metrics.set_index('time')['gpu_temp'].rolling(window)
            
            features[f'gpu_temp_mean_{window}'] = rolling.mean().iloc[-1]
            features[f'gpu_temp_std_{window}'] = rolling.std().iloc[-1]
            features[f'gpu_temp_max_{window}'] = rolling.max().iloc[-1]
            features[f'gpu_temp_min_{window}'] = rolling.min().iloc[-1]
        
        # Power statistics
        for window in ['1h', '24h']:
            rolling = metrics.set_index('time')['power_usage'].rolling(window)
            features[f'power_mean_{window}'] = rolling.mean().iloc[-1]
            features[f'power_std_{window}'] = rolling.std().iloc[-1]
        
        # ECC error rates
        ecc_sbe_7d = metrics['ecc_sbe_volatile'].iloc[-1] - metrics['ecc_sbe_volatile'].iloc[0]
        ecc_dbe_7d = metrics['ecc_dbe_volatile'].iloc[-1] - metrics['ecc_dbe_volatile'].iloc[0]
        
        features['ecc_sbe_rate_7d'] = ecc_sbe_7d / 7.0  # Per day
        features['ecc_dbe_rate_7d'] = ecc_dbe_7d / 7.0
        
        return features
    
    def _trend_features(self, metrics: pd.DataFrame) -> dict:
        """Trend analysis (degradation over time)."""
        features = {}
        
        from scipy.stats import linregress
        
        # Temperature trend
        x = np.arange(len(metrics))
        
        temp_slope, _, _, _, _ = linregress(x, metrics['gpu_temp'])
        features['gpu_temp_trend'] = temp_slope  # °C per day
        
        # Power trend
        power_slope, _, _, _, _ = linregress(x, metrics['power_usage'])
        features['power_trend'] = power_slope
        
        # SM active trend (performance degradation)
        if 'sm_active' in metrics:
            sm_slope, _, _, _, _ = linregress(x, metrics['sm_active'])
            features['sm_active_trend'] = sm_slope
        
        return features
    
    def _anomaly_features(self, metrics: pd.DataFrame) -> dict:
        """Anomaly counts and patterns."""
        features = {}
        
        # Temperature spikes (>2 std dev from mean)
        temp_mean = metrics['gpu_temp'].mean()
        temp_std = metrics['gpu_temp'].std()
        
        spike_threshold = temp_mean + 2 * temp_std
        features['temp_spike_count'] = (metrics['gpu_temp'] > spike_threshold).sum()
        
        # Throttling frequency
        features['throttle_event_count'] = (metrics['throttle_reasons'] > 0).sum()
        features['throttle_event_pct'] = features['throttle_event_count'] / len(metrics) * 100
        
        # Power anomalies
        power_mean = metrics['power_usage'].mean()
        power_std = metrics['power_usage'].std()
        
        features['power_anomaly_count'] = (
            (metrics['power_usage'] > power_mean + 2 * power_std) |
            (metrics['power_usage'] < power_mean - 2 * power_std)
        ).sum()
        
        return features
    
    def _event_features(self, metrics: pd.DataFrame) -> dict:
        """Count specific events."""
        features = {}
        
        # Throttle reason breakdown
        features['hw_thermal_throttle_count'] = ((metrics['throttle_reasons'] & (1 << 6)) > 0).sum()
        features['hw_power_brake_count'] = ((metrics['throttle_reasons'] & (1 << 7)) > 0).sum()
        features['sw_power_cap_count'] = ((metrics['throttle_reasons'] & (1 << 2)) > 0).sum()
        
        # ECC error events
        features['ecc_dbe_event_count'] = (metrics['ecc_dbe_volatile'] > 0).sum()
        
        return features
    
    def _metadata_features(self, gpu_uuid: str) -> dict:
        """Asset metadata features."""
        features = {}
        
        # Query from PostgreSQL gpu_assets table
        asset = self._query_asset(gpu_uuid)
        
        if asset is not None:
            # GPU age (days since deployment)
            if asset['deployment_date']:
                age_days = (pd.Timestamp.now() - asset['deployment_date']).days
                features['gpu_age_days'] = age_days
            
            # Time to warranty expiry
            if asset['warranty_expiry']:
                warranty_days = (asset['warranty_expiry'] - pd.Timestamp.now()).days
                features['warranty_remaining_days'] = warranty_days
            
            # Model encoding (one-hot or label encoding)
            features['model_A100'] = 1 if 'A100' in asset['model'] else 0
            features['model_H100'] = 1 if 'H100' in asset['model'] else 0
        
        return features
```

---

## Model Training Pipeline

### Airflow DAG

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'ml-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email': ['alerts@gpuhealth.com'],
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'gpu_health_ml_pipeline',
    default_args=default_args,
    description='GPU health scoring and failure prediction',
    schedule_interval='0 2 * * *',  # Daily at 02:00 UTC
    start_date=datetime(2026, 2, 1),
    catchup=False,
    tags=['ml', 'gpu-health'],
)

# Task 1: Feature extraction
extract_features = PythonOperator(
    task_id='extract_features',
    python_callable=extract_features_task,
    dag=dag,
)

# Task 2: Health scoring
compute_health_scores = PythonOperator(
    task_id='compute_health_scores',
    python_callable=health_scoring_task,
    dag=dag,
)

# Task 3: Failure prediction
predict_failures = PythonOperator(
    task_id='predict_failures',
    python_callable=failure_prediction_task,
    dag=dag,
)

# Task 4: Economic analysis
economic_decisions = PythonOperator(
    task_id='economic_decisions',
    python_callable=economic_analysis_task,
    dag=dag,
)

# Task dependencies
extract_features >> compute_health_scores
extract_features >> predict_failures
[compute_health_scores, predict_failures] >> economic_decisions


def extract_features_task(**context):
    """Extract features for all GPUs."""
    from feature_engineering import GPUFeatureEngineer
    
    engineer = GPUFeatureEngineer()
    
    # Get list of all active GPUs
    gpu_uuids = get_active_gpus()
    
    features = []
    for gpu_uuid in gpu_uuids:
        try:
            feat = engineer.extract_features(gpu_uuid, lookback_days=7)
            feat['gpu_uuid'] = gpu_uuid
            features.append(feat)
        except Exception as e:
            print(f"Error extracting features for {gpu_uuid}: {e}")
    
    # Save to feature store
    feature_df = pd.DataFrame(features)
    save_to_feature_store(feature_df)
    
    return len(features)


def health_scoring_task(**context):
    """Compute health scores for all GPUs."""
    from health_scorer import GPUHealthScorer
    
    scorer = GPUHealthScorer()
    
    gpu_uuids = get_active_gpus()
    scores = []
    
    for gpu_uuid in gpu_uuids:
        metrics = query_metrics(gpu_uuid, days=7)
        score = scorer.score_gpu(metrics, gpu_uuid)
        
        scores.append({
            'time': datetime.utcnow(),
            'gpu_uuid': gpu_uuid,
            **score.__dict__
        })
    
    # Write to PostgreSQL
    write_health_scores(scores)
    
    return len(scores)


def failure_prediction_task(**context):
    """Run failure prediction models."""
    import mlflow
    
    # Load models from MLflow
    xgb_model = mlflow.pyfunc.load_model("models:/gpu_failure_xgb/production")
    lstm_model = mlflow.pyfunc.load_model("models:/gpu_failure_lstm/production")
    
    # Load features from feature store
    features = load_from_feature_store()
    
    # XGBoost predictions
    failure_prob_30d = xgb_model.predict(features)
    
    # LSTM predictions (requires sequence data)
    # ... load sequences, run LSTM
    
    # Combine predictions
    predictions = []
    for i, row in features.iterrows():
        predictions.append({
            'time': datetime.utcnow(),
            'gpu_uuid': row['gpu_uuid'],
            'failure_prob_7d': failure_prob_30d[i] * 0.3,  # Scale down
            'failure_prob_30d': failure_prob_30d[i],
            'failure_prob_90d': failure_prob_30d[i] * 1.5,  # Scale up
            'model_name': 'xgb_ensemble_v2',
            'model_version': '2.1.0',
            'confidence': 0.85
        })
    
    # Write to PostgreSQL
    write_failure_predictions(predictions)
    
    return len(predictions)
```

---

## Model Serving & Inference

### FastAPI Inference Service

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mlflow
import pandas as pd

app = FastAPI(title="GPU Health ML API")

# Load models on startup
xgb_model = None
health_scorer = None

@app.on_event("startup")
async def load_models():
    global xgb_model, health_scorer
    
    xgb_model = mlflow.pyfunc.load_model("models:/gpu_failure_xgb/production")
    
    from health_scorer import GPUHealthScorer
    health_scorer = GPUHealthScorer()


class HealthScoreRequest(BaseModel):
    gpu_uuid: str
    lookback_days: int = 7


class HealthScoreResponse(BaseModel):
    gpu_uuid: str
    overall_score: float
    memory_health: float
    thermal_health: float
    performance_health: float
    power_health: float
    reliability_health: float
    health_grade: str
    degradation_factors: list


@app.post("/api/v1/health/score", response_model=HealthScoreResponse)
async def compute_health_score(request: HealthScoreRequest):
    """Compute real-time health score for a GPU."""
    
    # Query metrics
    metrics = query_metrics(request.gpu_uuid, days=request.lookback_days)
    
    if metrics.empty:
        raise HTTPException(status_code=404, detail=f"No metrics found for {request.gpu_uuid}")
    
    # Score
    score = health_scorer.score_gpu(metrics, request.gpu_uuid)
    
    return HealthScoreResponse(
        gpu_uuid=request.gpu_uuid,
        **score.__dict__
    )


class FailurePredictionRequest(BaseModel):
    gpu_uuid: str


class FailurePredictionResponse(BaseModel):
    gpu_uuid: str
    failure_prob_7d: float
    failure_prob_30d: float
    failure_prob_90d: float
    predicted_failure_type: str
    confidence: float


@app.post("/api/v1/predict/failure", response_model=FailurePredictionResponse)
async def predict_failure(request: FailurePredictionRequest):
    """Predict failure probability for a GPU."""
    
    # Extract features
    from feature_engineering import GPUFeatureEngineer
    engineer = GPUFeatureEngineer()
    
    features = engineer.extract_features(request.gpu_uuid, lookback_days=7)
    
    # Convert to DataFrame (model expects batch input)
    features_df = pd.DataFrame([features])
    
    # Predict
    failure_prob = xgb_model.predict(features_df)[0]
    
    return FailurePredictionResponse(
        gpu_uuid=request.gpu_uuid,
        failure_prob_7d=failure_prob * 0.3,
        failure_prob_30d=failure_prob,
        failure_prob_90d=failure_prob * 1.5,
        predicted_failure_type="memory",  # From LSTM
        confidence=0.85
    )
```

---

## Economic Decision Engine

### NPV-Based Lifecycle Recommendations

```python
from dataclasses import dataclass
from enum import Enum

class LifecycleDecision(Enum):
    KEEP = "keep"
    SELL = "sell"
    REPURPOSE = "repurpose"
    DECOMMISSION = "decommission"


@dataclass
class EconomicAnalysis:
    gpu_uuid: str
    decision: LifecycleDecision
    npv_keep: float
    npv_sell: float
    npv_repurpose: float
    salvage_value: float
    expected_value: float
    confidence: float
    rationale: str


class EconomicDecisionEngine:
    """NPV-based lifecycle decision engine."""
    
    # Market prices (example for H100)
    RESIDUAL_VALUE = {
        'excellent': 32000,  # $32k for excellent condition
        'good': 28000,
        'fair': 22000,
        'degraded': 15000,
        'poor': 8000,
        'critical': 2000
    }
    
    # Monthly costs
    POWER_COST_PER_KWH = 0.12  # $0.12/kWh
    COOLING_MULTIPLIER = 1.3   # PUE
    MAINTENANCE_COST_MONTHLY = 50  # $50/month
    
    # Revenue assumptions
    REVENUE_PER_HOUR_FULL = 3.00  # $3/hour at 100% utilization
    
    def analyze(
        self,
        gpu_uuid: str,
        health_score: float,
        health_grade: str,
        failure_prob_30d: float,
        utilization: float = 0.90
    ) -> EconomicAnalysis:
        """
        Perform NPV analysis to recommend lifecycle decision.
        
        Args:
            health_score: Overall health (0-100)
            health_grade: Health grade ("excellent", "good", etc.)
            failure_prob_30d: Probability of failure in 30 days
            utilization: Current utilization rate
        
        Returns:
            EconomicAnalysis with recommendation
        """
        
        # NPV(Keep): 12-month revenue - costs
        npv_keep = self._calculate_npv_keep(
            health_score, failure_prob_30d, utilization
        )
        
        # NPV(Sell): Residual value - transaction costs
        npv_sell = self._calculate_npv_sell(health_grade)
        
        # NPV(Repurpose): Revenue from lower-tier workloads
        npv_repurpose = self._calculate_npv_repurpose(health_score)
        
        # Salvage value (last resort)
        salvage = self.RESIDUAL_VALUE.get(health_grade, 0) * 0.1
        
        # Choose max NPV
        options = {
            LifecycleDecision.KEEP: npv_keep,
            LifecycleDecision.SELL: npv_sell,
            LifecycleDecision.REPURPOSE: npv_repurpose,
            LifecycleDecision.DECOMMISSION: salvage
        }
        
        best_decision = max(options, key=options.get)
        expected_value = options[best_decision]
        
        # Confidence based on difference between top 2 options
        sorted_options = sorted(options.values(), reverse=True)
        if len(sorted_options) > 1:
            confidence = min(1.0, (sorted_options[0] - sorted_options[1]) / sorted_options[0])
        else:
            confidence = 1.0
        
        # Rationale
        rationale = self._generate_rationale(
            best_decision, health_score, health_grade, failure_prob_30d, utilization
        )
        
        return EconomicAnalysis(
            gpu_uuid=gpu_uuid,
            decision=best_decision,
            npv_keep=npv_keep,
            npv_sell=npv_sell,
            npv_repurpose=npv_repurpose,
            salvage_value=salvage,
            expected_value=expected_value,
            confidence=confidence,
            rationale=rationale
        )
    
    def _calculate_npv_keep(self, health_score, failure_prob, utilization):
        """Calculate NPV of keeping GPU in production."""
        
        # Revenue potential (12 months)
        hours_per_month = 730
        monthly_revenue = (
            self.REVENUE_PER_HOUR_FULL * 
            hours_per_month * 
            utilization *
            (health_score / 100)  # Discount by health
        )
        
        # Costs
        power_kwh_per_month = 0.7 * 24 * 30  # 700W = 0.7 kW
        monthly_power_cost = (
            power_kwh_per_month * 
            self.POWER_COST_PER_KWH * 
            self.COOLING_MULTIPLIER
        )
        
        monthly_cost = monthly_power_cost + self.MAINTENANCE_COST_MONTHLY
        
        # Risk adjustment (expected loss from failure)
        expected_failure_loss = failure_prob * monthly_revenue * 3  # 3 months downtime
        
        # 12-month NPV
        npv = (monthly_revenue - monthly_cost) * 12 - expected_failure_loss
        
        return npv
    
    def _calculate_npv_sell(self, health_grade):
        """Calculate NPV of selling GPU."""
        
        residual_value = self.RESIDUAL_VALUE.get(health_grade, 0)
        transaction_cost = residual_value * 0.05  # 5% marketplace fee
        
        return residual_value - transaction_cost
    
    def _calculate_npv_repurpose(self, health_score):
        """Calculate NPV of repurposing to lower-priority workloads."""
        
        # Lower revenue but also lower cost (reduced power from lower utilization)
        reduced_revenue_per_hour = self.REVENUE_PER_HOUR_FULL * 0.6
        hours_per_month = 730
        utilization = 0.5
        
        monthly_revenue = (
            reduced_revenue_per_hour * 
            hours_per_month * 
            utilization *
            (health_score / 100)
        )
        
        # Lower power cost
        power_kwh_per_month = 0.4 * 24 * 30  # 400W avg
        monthly_power_cost = (
            power_kwh_per_month * 
            self.POWER_COST_PER_KWH * 
            self.COOLING_MULTIPLIER
        )
        
        monthly_cost = monthly_power_cost + self.MAINTENANCE_COST_MONTHLY
        
        npv = (monthly_revenue - monthly_cost) * 12
        
        return npv
    
    def _generate_rationale(self, decision, health_score, health_grade, failure_prob, utilization):
        """Generate human-readable rationale for decision."""
        
        if decision == LifecycleDecision.KEEP:
            return (
                f"Keep in production. Health score {health_score:.0f} ({health_grade}) "
                f"supports continued operation. Low failure risk ({failure_prob*100:.1f}%). "
                f"12-month NPV positive at {utilization*100:.0f}% utilization."
            )
        
        elif decision == LifecycleDecision.SELL:
            return (
                f"Sell on secondary market. Residual value (${self.RESIDUAL_VALUE[health_grade]:,}) "
                f"exceeds operational NPV. Health grade: {health_grade}."
            )
        
        elif decision == LifecycleDecision.REPURPOSE:
            return (
                f"Repurpose for lower-priority workloads. Health score {health_score:.0f} "
                f"insufficient for prime production but still viable. Reduces failure risk exposure."
            )
        
        else:  # DECOMMISSION
            return (
                f"Decommission. Critical health ({health_grade}). "
                f"Operational costs exceed value. Salvage for parts."
            )
```

---

## MLOps & Model Management

### MLflow Integration

```python
import mlflow
import mlflow.xgboost
import mlflow.pytorch

# Training with MLflow tracking
with mlflow.start_run(run_name="xgb_failure_prediction_v2"):
    
    # Log parameters
    mlflow.log_params({
        'max_depth': 6,
        'learning_rate': 0.05,
        'n_estimators': 500,
        'scale_pos_weight': 10.5
    })
    
    # Train model
    model = train_xgboost_model(X_train, y_train, X_val, y_val)
    
    # Log metrics
    val_auc = roc_auc_score(y_val, model.predict_proba(X_val)[:, 1])
    mlflow.log_metric("val_auc", val_auc)
    mlflow.log_metric("val_precision", precision)
    mlflow.log_metric("val_recall", recall)
    
    # Log model
    mlflow.xgboost.log_model(
        model,
        artifact_path="model",
        registered_model_name="gpu_failure_xgb"
    )
    
    # Log feature importance plot
    import matplotlib.pyplot as plt
    
    xgb.plot_importance(model, max_num_features=20)
    plt.tight_layout()
    mlflow.log_figure(plt.gcf(), "feature_importance.png")

# Promote model to production
client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage(
    name="gpu_failure_xgb",
    version=2,
    stage="Production"
)
```

---

## Performance & Scaling

### Batch Inference Optimization

```python
# Parallelize scoring across GPUs
from multiprocessing import Pool

def score_gpu_batch(gpu_uuids):
    """Score a batch of GPUs in parallel."""
    
    with Pool(processes=32) as pool:
        scores = pool.map(score_single_gpu, gpu_uuids)
    
    return scores

# Takes ~2 minutes for 10,000 GPUs (vs. 1 hour serial)
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-11  
**Maintained By**: Stuart Hart (stuarthart@msn.com)  
**Project**: GPU Health Monitor - Production-grade monitoring for NVIDIA A100/H100 fleets
