import pandas as pd
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    average_precision_score
)

p = "outputs/reports/ward_flood_susceptibility_holdout.csv"
df = pd.read_csv(p)

y = df["actual_label"].astype(int)
prob = df["predicted_probability"]

print("=== PROBABILITY DISTRIBUTION ===")
print(prob.describe(percentiles=[.5, .75, .90, .95, .99]).to_string())
print("\nActual positive rate:", round(y.mean(), 4))
print("Average precision:", round(average_precision_score(y, prob), 4))

print("\n=== THRESHOLD DIAGNOSTIC ===")
print("threshold | precision | recall | F1 | predicted positives")
for t in [.01, .02, .03, .05, .075, .10, .15, .20, .30, .50]:
    pred = (prob >= t).astype(int)
    print(
        f"{t:9.3f} | "
        f"{precision_score(y, pred, zero_division=0):9.3f} | "
        f"{recall_score(y, pred, zero_division=0):6.3f} | "
        f"{f1_score(y, pred, zero_division=0):.3f} | "
        f"{int(pred.sum()):18d}"
    )

print("\n=== HIGHEST-SCORING CELLS ===")
print(
    df.nlargest(10, "predicted_probability")[
        ["grid_id", "ward", "actual_label", "predicted_probability"]
    ].to_string(index=False)
)
