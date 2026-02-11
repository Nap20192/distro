# Lab 6 — Spark ML Pipeline on Amazon EMR (Customer Churn)

## Overview
Built an end-to-end Spark ML pipeline on Amazon EMR to predict customer churn using the Kaggle Bank Customer Churn dataset. The pipeline runs on YARN and uses distributed feature engineering and model training.

## Dataset
**Source:** https://www.kaggle.com/datasets/shrutimechlearn/churn-modelling

**Target:** `Exited` (0 = No churn, 1 = Churn)

## Pipeline (Spark ML)
1. Data loading from HDFS
2. Categorical encoding (StringIndexer + OneHotEncoder)
3. Feature assembly (VectorAssembler)
4. Feature scaling (StandardScaler)
5. Model training (Logistic Regression)
6. Prediction
7. Evaluation (Accuracy)

## Code
Primary script: `churn_pipline.py`

## Run on EMR
```
spark-submit \
	--master yarn \
	--deploy-mode client \
	churn_pipline.py
```

## Experiment (Option B — Feature Ablation)
Removed categorical features and compared accuracy/runtime. See screenshots for evidence and results.

## Summary and Analysis
The screenshots together document a complete distributed ML workflow on EMR: the cluster is created and running, the churn dataset is placed in HDFS, and the Spark job is submitted from the master node. The pipeline logs confirm the ML stages (indexing, encoding, assembling, scaling, and training) execute on YARN, and sample predictions plus the printed accuracy validate the end-to-end flow. The YARN UI screenshot verifies distributed execution with active executors and stages. The experiment sequence shows a second run with categorical features removed; the reported accuracy/runtime demonstrates the impact of feature ablation and provides the required comparison. Overall, the evidence supports correct pipeline design, successful distributed execution, and a clear experimental observation.

## Result Summary
- Spark ML pipeline completed on EMR and produced predictions.
- Accuracy was computed successfully for the full feature set.
- Feature ablation run completed, enabling comparison of accuracy/runtime.

## Screenshots (Evidence)
### Screenshot 1 — EMR cluster created and running
Cluster state in AWS EMR console.

![EMR cluster](image.png)

### Screenshot 2 — Dataset staged in HDFS
`hdfs dfs -ls /user/hadoop/churn_input` showing the CSV.

![HDFS dataset](image%20copy.png)

### Screenshot 3 — Spark job submission
`spark-submit` command executed on the EMR master.

![Spark submit](image%20copy%202.png)

### Screenshot 4 — Pipeline execution logs
Spark pipeline stages initializing and running.

![Pipeline output](image%20copy%203.png)

### Screenshot 5 — Model predictions sample
`Exited`, `prediction`, `probability` output preview.

![Predictions](image%20copy%204.png)

### Screenshot 6 — Evaluation metric
Accuracy printed by the evaluator.

![Accuracy](image%20copy%205.png)

### Screenshot 7 — YARN monitoring
Application and executor status in YARN UI.

![YARN UI](image%20copy%206.png)

### Screenshot 8 — Experiment run (feature ablation)
Script run without categorical features.

![Experiment run](image%20copy%207.png)

### Screenshot 9 — Experiment result
Accuracy/runtime reported for the ablated model.

![Experiment result](image%20copy%208.png)

### Screenshot 10 — Summary evidence
Consolidated view of key outputs/results.

![Summary](image%20copy%209.png)
