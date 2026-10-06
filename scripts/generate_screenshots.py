#!/usr/bin/env python3
"""
Generate screenshots/visualizations for QZero documentation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.metrics import confusion_matrix, roc_curve, auc
from sklearn.model_selection import train_test_split

from src.preprocessing.data_loader import generate_synthetic_data
from src.preprocessing.feature_engineering import FeatureEngineer
from src.classical.baseline import ClassicalBaseline

# Set style
plt.style.use('dark_background')
sns.set_palette("husl")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'screenshots')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_fig(name):
    path = os.path.join(OUTPUT_DIR, f"{name}.png")
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
    plt.close()
    print(f"Saved: {path}")

# 1. Generate synthetic data
print("Generating synthetic data...")
X, y = generate_synthetic_data(n_samples=2000, n_features=10, difficulty='medium')
# Convert to numpy if pandas DataFrame
if hasattr(X, 'values'):
    X = X.values
if hasattr(y, 'values'):
    y = y.values

# Ensure binary labels for classification
y_binary = (y > 0).astype(int)

# 2. Feature distribution
print("Creating feature distribution plot...")
fig, axes = plt.subplots(2, 5, figsize=(16, 6))
for i, ax in enumerate(axes.flat):
    ax.hist(X[:, i], bins=30, alpha=0.7, color='#6366f1', edgecolor='white', linewidth=0.5)
    ax.set_title(f'Feature {i+1}', fontsize=10, color='white')
    ax.tick_params(colors='white', labelsize=8)
fig.suptitle('QZero - Feature Distributions (Synthetic Data)', fontsize=14, color='white', y=1.02)
plt.tight_layout()
save_fig('01_feature_distributions')

# 3. PCA visualization
print("Creating PCA visualization...")
pca = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X)

fig, ax = plt.subplots(figsize=(10, 8))
scatter = ax.scatter(X_pca[:, 0], X_pca[:, 1], c=y_binary, cmap='coolwarm', alpha=0.6, s=20)
ax.set_xlabel('Principal Component 1', color='white')
ax.set_ylabel('Principal Component 2', color='white')
ax.set_title('QZero - PCA Projection (Normal vs Anomaly)', fontsize=14, color='white')
ax.tick_params(colors='white')
cbar = plt.colorbar(scatter)
cbar.ax.set_ylabel('Class (0=Normal, 1=Anomaly)', color='white')
cbar.ax.tick_params(colors='white')
save_fig('02_pca_visualization')

# 4. t-SNE visualization
print("Creating t-SNE visualization...")
tsne = TSNE(n_components=2, random_state=42, perplexity=30)
X_tsne = tsne.fit_transform(X[:500])  # Subset for speed

fig, ax = plt.subplots(figsize=(10, 8))
scatter = ax.scatter(X_tsne[:, 0], X_tsne[:, 1], c=y_binary[:500], cmap='coolwarm', alpha=0.7, s=30)
ax.set_xlabel('t-SNE Dimension 1', color='white')
ax.set_ylabel('t-SNE Dimension 2', color='white')
ax.set_title('QZero - t-SNE Projection (Anomaly Detection)', fontsize=14, color='white')
ax.tick_params(colors='white')
save_fig('03_tsne_visualization')

# 5. Train classical baseline and get results
print("Training classical baselines...")
X_train, X_test, y_train, y_test = train_test_split(X, y_binary, test_size=0.2, random_state=42)

models = ['random_forest', 'svm_rbf', 'gradient_boosting']
results = {}

for model_name in models:
    print(f"  Training {model_name}...")
    clf = ClassicalBaseline(model_name=model_name)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, 1]
    
    # ROC curve
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    roc_auc = auc(fpr, tpr)
    results[model_name] = {'fpr': fpr, 'tpr': tpr, 'auc': roc_auc, 'y_pred': y_pred}

# 6. ROC curves comparison
print("Creating ROC curves comparison...")
fig, ax = plt.subplots(figsize=(10, 8))
colors = ['#6366f1', '#10b981', '#f59e0b']
for (name, data), color in zip(results.items(), colors):
    ax.plot(data['fpr'], data['tpr'], color=color, lw=2, 
            label=f'{name.replace("_", " ").title()} (AUC = {data["auc"]:.3f})')
ax.plot([0, 1], [0, 1], 'w--', lw=1, alpha=0.5)
ax.set_xlabel('False Positive Rate', color='white', fontsize=12)
ax.set_ylabel('True Positive Rate', color='white', fontsize=12)
ax.set_title('QZero - ROC Curves: Classical Baselines', fontsize=14, color='white')
ax.legend(loc='lower right', facecolor='#1a1a2e', edgecolor='white', labelcolor='white')
ax.tick_params(colors='white')
ax.set_xlim([0, 1])
ax.set_ylim([0, 1.05])
save_fig('04_roc_curves')

# 7. Confusion matrix
print("Creating confusion matrix...")
cm = confusion_matrix(y_test, results['random_forest']['y_pred'])

fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax, 
            xticklabels=['Normal', 'Anomaly'], yticklabels=['Normal', 'Anomaly'],
            annot_kws={'size': 16, 'color': 'white'})
ax.set_xlabel('Predicted', fontsize=12, color='white')
ax.set_ylabel('Actual', fontsize=12, color='white')
ax.set_title('QZero - Confusion Matrix (Random Forest)', fontsize=14, color='white')
ax.tick_params(colors='white')
save_fig('05_confusion_matrix')

# 8. Model comparison bar chart
print("Creating model comparison...")
model_names = list(results.keys())
aucs = [results[m]['auc'] for m in model_names]

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(model_names, aucs, color=['#6366f1', '#10b981', '#f59e0b'], edgecolor='white')
ax.set_xlabel('AUC Score', color='white', fontsize=12)
ax.set_title('QZero - Model Performance Comparison', fontsize=14, color='white')
ax.tick_params(colors='white')
ax.set_xlim([0.5, 1.0])
for bar, auc_val in zip(bars, aucs):
    ax.text(auc_val + 0.01, bar.get_y() + bar.get_height()/2, f'{auc_val:.3f}', 
            va='center', color='white', fontsize=12)
save_fig('06_model_comparison')

# 9. Quantum circuit placeholder (ASCII art as image)
print("Creating quantum circuit diagram...")
fig, ax = plt.subplots(figsize=(12, 6))
ax.text(0.5, 0.5, '''
╔═══════════════════════════════════════════════════════════════╗
║           QZero Quantum Feature Map Circuit                    ║
╠═══════════════════════════════════════════════════════════════╣
║                                                                 ║
║   q0: ─────H─────●───RZ(x₀)────────●───────RZ(x₄)───────●─────║
║               │                    │                        ║
║   q1: ─────H───┼───RZ(x₁)─────●────┼───────RZ(x₅)───────┼─────║
║               │        │        │    │                 │     ║
║   q2: ─────H───┼───────┼──RZ(x₂)─┼────X───────RZ(x₆)───X─────║
║               │        │         │    │                 │     ║
║   q3: ─────H───X───────X────────X────X───────RZ(x₇)──────X────║
║                                                                 ║
║   ZZ Entanglement:  ━━━━━━━━━━━━━━━━━━━━━━━━                   ║
║                                                                 ║
║   Encoding: 10 classical features → 4 qubits                  ║
╚══════════════════════════════════════════════════════════════════╝
''', fontsize=11, fontfamily='monospace', color='#10b981',
     ha='center', va='center', transform=ax.transAxes)
ax.set_xlim([0, 1])
ax.set_ylim([0, 1])
ax.axis('off')
ax.set_title('QZero - Quantum Feature Map (ZZ Encoding)', fontsize=14, color='white', y=0.95)
save_fig('07_quantum_circuit')

# 10. API endpoint diagram
print("Creating API endpoint diagram...")
fig, ax = plt.subplots(figsize=(14, 9))

endpoints = [
    ('POST /analyze', 'Analyze traffic (NetFlow/PCAP)'),
    ('POST /train', 'Train on custom dataset'),
    ('GET  /health', 'Health check endpoint'),
    ('GET  /models', 'List available models'),
    ('POST /export', 'Export predictions/JSON'),
    ('GET  /dashboard', 'Streamlit web UI'),
]

for i, (endpoint, desc) in enumerate(endpoints):
    y_pos = i * 0.15 + 0.75
    ax.text(0.05, y_pos, endpoint, color='#10b981', fontsize=13, fontweight='bold')
    ax.text(0.5, y_pos, desc, color='#8b949e', fontsize=11)

# Draw box container
rect = plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                      facecolor='#161b22', edgecolor='#30363d', lw=3, zorder=-1)
ax.add_patch(rect)

ax.text(0.05, 0.97, 'QZero REST API Endpoints', color='#58a6ff', fontsize=16, fontweight='bold')
ax.set_xlim([0, 1])
ax.set_ylim([0, 1])
ax.axis('off')
save_fig('08_api_endpoints')

print("\n✅ All screenshots generated successfully!")
print(f"Output directory: {OUTPUT_DIR}")