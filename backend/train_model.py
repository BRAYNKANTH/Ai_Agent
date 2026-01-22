import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report
import os

def train_spam_filter():
    # 1. Load Data
    data_path = "backend/training_data/unified_spam_data.csv"
    if not os.path.exists(data_path):
        print("❌ Unified data not found. Run unify_data.py first.")
        return

    print("📊 Loading dataset...")
    df = pd.read_csv(data_path)
    
    # Handle missing values just in case
    df['text'] = df['text'].fillna('')

    X = df['text']
    y = df['label']

    # 2. Split
    print("✂️ Splitting data...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Vectorization (TF-IDF)
    print("🔠 Vectorizing text (TF-IDF)...")
    vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # 4. Train Model (Naive Bayes)
    print("🧠 Training Naive Bayes Model...")
    classifier = MultinomialNB()
    classifier.fit(X_train_vec, y_train)

    # 5. Evaluate
    print("📈 Evaluating...")
    predictions = classifier.predict(X_test_vec)
    accuracy = accuracy_score(y_test, predictions)
    print(f"\n🏆 Model Accuracy: {accuracy * 100:.2f}%")
    print("\nClassification Report:")
    print(classification_report(y_test, predictions))

    # 6. Save Artifacts
    models_dir = "backend/app/models"
    os.makedirs(models_dir, exist_ok=True)
    
    print(f"💾 Saving model to {models_dir}...")
    joblib.dump(classifier, f"{models_dir}/spam_classifier.pkl")
    joblib.dump(vectorizer, f"{models_dir}/tfidf_vectorizer.pkl")
    print("✅ Training Complete and Saved!")

if __name__ == "__main__":
    train_spam_filter()
