import pandas as pd
import glob
import os

def unify_datasets():
    all_files = glob.glob("backend/training_data/*.csv")
    print(f"Found {len(all_files)} files.")

    unified_data = []

    for file in all_files:
        try:
            df = pd.read_csv(file, encoding='latin-1') # encoding fallback often needed for spam data
            print(f"Processing {os.path.basename(file)} | Columns: {list(df.columns)}")
            
            # Map columns
            # Standard: 'text' and 'label' (1=Spam, 0=Ham)
            
            # 1. SMS_train.csv / SMS_test.csv: 'Message_body', 'Label' ('Spam'/'Non-Spam')
            if 'Message_body' in df.columns:
                df = df.rename(columns={'Message_body': 'text', 'Label': 'label'})
                df['label'] = df['label'].map({'Spam': 1, 'Non-Spam': 0})
            
            # 2. Enron.csv: 'body', 'label' ('Spam'/'Ham' ?) or 1/0
            elif 'body' in df.columns and 'label' in df.columns:
                df = df.rename(columns={'body': 'text'})
                # Check label type
                if df['label'].dtype == 'object':
                     df['label'] = df['label'].map({'Spam': 1, 'Ham': 0, 'spam': 1, 'ham': 0})
            
            # 3. Phishing: 'text_combined', 'label'
            elif 'text_combined' in df.columns:
                 df = df.rename(columns={'text_combined': 'text'})
                 # Likely already 1/0 but just in case
            
            # 4. Fallback for generic 'text'/'label' if exist
            elif 'text' in df.columns and 'label' in df.columns:
                pass # Good
            
            else:
                print(f"⚠️ Skipping {file}: Could not map columns.")
                continue

            # Clean and Select
            df = df[['text', 'label']]
            df['label'] = pd.to_numeric(df['label'], errors='coerce')
            df = df.dropna()

            unified_data.append(df)
            print(f"✅ Added {len(df)} rows from {os.path.basename(file)}")

        except Exception as e:
            print(f"❌ Error processing {file}: {e}")

    if not unified_data:
        print("No data loaded!")
        return

    # Merge
    master_df = pd.concat(unified_data, ignore_index=True)
    
    # Final cleanup
    master_df['label'] = master_df['label'].astype(int)
    master_df = master_df.drop_duplicates(subset=['text'])
    
    output_path = "backend/training_data/unified_spam_data.csv"
    master_df.to_csv(output_path, index=False)
    print(f"\n🎉 Success! Unified dataset saved to {output_path}")
    print(f"Total Samples: {len(master_df)}")
    print(f"Spam Count: {len(master_df[master_df['label']==1])}")
    print(f"Ham Count: {len(master_df[master_df['label']==0])}")

if __name__ == "__main__":
    unify_datasets()
