import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
import os

def train_intent_model():
    # 1. Load Data
    data_path = "backend/training_data/unified_intent_data.csv"
    if not os.path.exists(data_path):
        print("❌ Unified intent data not found. Run unify_intent.py first.")
        return

    print("📊 Loading Intent Data...")
    df = pd.read_csv(data_path)
    df['text'] = df['text'].fillna('')
    df['label'] = df['label'].fillna('Uncategorized')

    # 2. Preprocess Multi-Labels
    print("🔖 Processing Multi-Labels...")
    # Convert string "Urgent,Finance" -> list ["Urgent", "Finance"]
    y = [label.split(",") for label in df['label']]
    
    mlb = MultiLabelBinarizer()
    y_encoded = mlb.fit_transform(y)
    
    print(f"Classes Found: {mlb.classes_}")

    X = df['text']

    # 3. Split
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

    # 4. Pipeline: TF-IDF -> LinearSVC (Wrapped in OneVsRest)
    # Using CalibratedClassifierCV to get probabilities from LinearSVC
    print("🧠 Training Multi-Label SVM...")
    
    svm = LinearSVC(class_weight='balanced', random_state=42)
    cutoff_svm = CalibratedClassifierCV(svm) # Calibrate for probability
    
    pipeline = Pipeline([
        ('vectorizer', TfidfVectorizer(stop_words='english', max_features=5000)),
        ('classifier', OneVsRestClassifier(cutoff_svm))
    ])

    pipeline.fit(X_train, y_train)

    # 5. Evaluate
    print("📈 Evaluating...")
    predictions = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    print(f"\n🏆 Model Subset Accuracy: {accuracy * 100:.2f}%")
    print("(Subset accuracy is harsh; it requires ALL labels to match perfectly)")
    
    # 6. Save Artifacts
    models_dir = "backend/app/models"
    os.makedirs(models_dir, exist_ok=True)
    
    print(f"💾 Saving intent model to {models_dir}...")
    joblib.dump(pipeline, f"{models_dir}/intent_pipeline.pkl")
    joblib.dump(mlb, f"{models_dir}/intent_mlb.pkl")
    print("✅ Intent Training Complete and Saved!")

if __name__ == "__main__":
    train_intent_model()
