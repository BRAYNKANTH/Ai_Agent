import pandas as pd
import glob
import os
import re

def unify_intent_datasets():
    # Folder containing the new intent CSVs
    raw_folder = "backend/training_data/intent_raw"
    all_files = glob.glob(f"{raw_folder}/*.csv")
    print(f"📂 Found {len(all_files)} files in {raw_folder}")

    unified_data = []

    # Standard Categories to map towards
    # We will try to fuzzy matches to these
    VALID_CATEGORIES = {
        'urgent': 'Urgent',
        'action': 'Urgent',
        'critical': 'Urgent',
        'finance': 'Finance',
        'invoice': 'Finance',
        'payment': 'Finance',
        'bill': 'Finance',
        'bank': 'Finance',
        'meeting': 'Meeting',
        'calendar': 'Meeting',
        'schedule': 'Meeting',
        'work': 'Work',
        'project': 'Work',
        'job': 'Work',
        'spam': 'Spam',
        'junk': 'Spam',
        'phishing': 'Phishing',
        'security': 'Phishing',
        'newsletter': 'Newsletter',
        'marketing': 'Newsletter',
        'promotion': 'Newsletter',
        'personal': 'Personal',
        'family': 'Personal',
        'social': 'Personal',
        'notification': 'Notification',
        'alert': 'Notification',
        'system': 'Notification',
        'receipt': 'Receipts',
        'order': 'Receipts',
        'purchase': 'Receipts',
        'shipping': 'Receipts'
    }

    for file in all_files:
        try:
            print(f"Processing {os.path.basename(file)}...")
            df = pd.read_csv(file, encoding='latin-1')
            
            # 1. Fuzzy Column Matching
            text_col = None
            label_col = None
            
            cols = [c.lower() for c in df.columns]
            
            # Find Text Column
            for candidate in ['body', 'text', 'message', 'content', 'email_text', 'subject']:
                if candidate in cols:
                    text_col = df.columns[cols.index(candidate)]
                    break
            
            # Find Label Column
            # Some files might have 'label', 'lable', 'category', 'new_category'
            for candidate in ['label', 'lable', 'labels', 'category', 'new_category', 'type', 'class']:
                # Exact match first
                if candidate in cols:
                     label_col = df.columns[cols.index(candidate)]
                     break
            
            if not text_col or not label_col:
                print(f"⚠️ Skipping {file}: Could not find text/label columns. (Found: {df.columns.tolist()})")
                continue

            # 2. Rename and Select
            df = df.rename(columns={text_col: 'text', label_col: 'raw_label'})
            df = df[['text', 'raw_label']]

            # 3. Clean Blank Rows
            initial_count = len(df)
            df = df.dropna(subset=['text', 'raw_label'])
            df = df[df['text'].str.strip() != '']
            df = df[df['raw_label'].str.strip() != '']
            print(f"   🧹 Removed {initial_count - len(df)} blank rows.")

            # 4. Standardize Labels (Multi-Label Logic)
            def clean_labels(raw):
                if not isinstance(raw, str): return "Uncategorized"
                
                # Split by common delimiters
                parts = re.split(r'[|,;]', raw)
                cleaned = set()
                
                for p in parts:
                    p_lower = p.strip().lower()
                    # Try to map to standard category
                    for key, standard in VALID_CATEGORIES.items():
                        if key in p_lower:
                            cleaned.add(standard)
                            break
                    else:
                        # Keep original if no map found, but capitalized
                        if len(p) > 2:
                             cleaned.add(p.title())
                
                return ",".join(list(cleaned))

            df['label'] = df['raw_label'].apply(clean_labels)
            
            # Drop Uncategorized if training data implies it
            df = df[df['label'] != '']
            
            unified_data.append(df[['text', 'label']])
            print(f"   ✅ Added {len(df)} rows.")

        except Exception as e:
            print(f"❌ Error processing {file}: {e}")

    # Merge
    if not unified_data:
        print("No valid data found!")
        return

    master_df = pd.concat(unified_data, ignore_index=True)
    master_df = master_df.drop_duplicates(subset=['text'])
    
    # Save
    master_df.to_csv("backend/training_data/unified_intent_data.csv", index=False)
    print(f"\n🎉 Unified Intent Data Saved! Total Samples: {len(master_df)}")
    print("Top Categories:\n", master_df['label'].value_counts().head(10))

if __name__ == "__main__":
    unify_intent_datasets()
