import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import sqlite3
from tqdm import tqdm
import nltk
from nltk.tokenize import word_tokenize
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud

# Download required NLTK data
nltk.download('punkt')

# Set style for plots
plt.style.use('seaborn')
sns.set_palette('husl')

class EURLexEDA:
    def __init__(self, data_dir='../data', db_path='eurlex_documents.db'):
        self.data_dir = Path(data_dir)
        self.db_path = db_path
        self.conn = None
        self.df = None
        
    def create_database(self):
        """Create SQLite database and load all JSON files."""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Create main documents table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            celex TEXT PRIMARY KEY,
            title TEXT,
            document_type TEXT,
            year INTEGER,
            number INTEGER,
            date_document DATE,
            date_effect DATE,
            date_end DATE,
            directory_code TEXT,
            full_text TEXT,
            author TEXT,
            form TEXT,
            subject_matter TEXT
        )
        """)
        
        # Create eurovoc_descriptors table with many-to-many relationship
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS eurovoc_descriptors (
            celex TEXT,
            descriptor TEXT,
            PRIMARY KEY (celex, descriptor),
            FOREIGN KEY (celex) REFERENCES documents(celex)
        )
        """)
        
        # Load JSON files
        json_files = list(self.data_dir.rglob('*.json'))
        print(f"Found {len(json_files)} JSON files")
        
        for file in tqdm(json_files, desc='Loading documents'):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    
                    # Insert into documents table
                    cursor.execute("""
                    INSERT OR REPLACE INTO documents 
                    (celex, title, document_type, year, number, date_document, 
                     date_effect, date_end, directory_code, full_text, author,
                     form, subject_matter)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        data.get('celex'),
                        data.get('title'),
                        data.get('document_type'),
                        data.get('year'),
                        data.get('number'),
                        data.get('date_document'),
                        data.get('date_effect'),
                        data.get('date_end'),
                        data.get('directory_code'),
                        data.get('full_text'),
                        data.get('author'),
                        data.get('form'),
                        data.get('subject_matter')
                    ))
                    
                    # Insert eurovoc descriptors
                    if 'eurovoc_descriptors' in data:
                        for descriptor in data['eurovoc_descriptors']:
                            cursor.execute("""
                            INSERT OR REPLACE INTO eurovoc_descriptors (celex, descriptor)
                            VALUES (?, ?)
                            """, (data['celex'], descriptor))
                    
            except json.JSONDecodeError:
                print(f"Error loading {file}")
                continue
        
        self.conn.commit()
        print("Database created successfully")
    
    def load_dataframe(self):
        """Load data from SQLite into pandas DataFrame."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
        
        # Load main document data
        self.df = pd.read_sql("""
        SELECT d.*, GROUP_CONCAT(e.descriptor) as eurovoc_descriptors
        FROM documents d
        LEFT JOIN eurovoc_descriptors e ON d.celex = e.celex
        GROUP BY d.celex
        """, self.conn)
        
        # Convert dates
        date_columns = ['date_document', 'date_effect', 'date_end']
        for col in date_columns:
            self.df[col] = pd.to_datetime(self.df[col])
        
        # Convert eurovoc_descriptors from string to list
        self.df['eurovoc_descriptors'] = self.df['eurovoc_descriptors'].apply(
            lambda x: x.split(',') if pd.notna(x) else []
        )
        
        print(f"Loaded {len(self.df)} documents into DataFrame")
    
    def basic_statistics(self):
        """Calculate and display basic statistics about the dataset."""
        print("=== Basic Dataset Statistics ===")
        print(f"\nTotal number of documents: {len(self.df)}")
        
        print("\nDocument types distribution:")
        print(self.df['document_type'].value_counts())
        
        print("\nYearly document counts:")
        print(self.df['year'].value_counts().sort_index())
        
        print("\nMost common authors:")
        print(self.df['author'].value_counts().head())
        
        print("\nMost common forms:")
        print(self.df['form'].value_counts().head())
        
        # Plot yearly trends
        plt.figure(figsize=(15, 6))
        self.df['year'].value_counts().sort_index().plot(kind='bar')
        plt.title('Number of Documents per Year')
        plt.xlabel('Year')
        plt.ylabel('Number of Documents')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    def text_analysis(self):
        """Analyze text content of documents."""
        print("=== Text Analysis ===")
        
        # Calculate text lengths
        self.df['text_length'] = self.df['full_text'].str.len()
        self.df['word_count'] = self.df['full_text'].apply(
            lambda x: len(word_tokenize(x)) if pd.notna(x) else 0
        )
        
        print("\nText length statistics:")
        print(self.df[['text_length', 'word_count']].describe())
        
        print("\nAverage text length by document type:")
        print(self.df.groupby('document_type')['text_length'].mean().sort_values(ascending=False))
        
        # Plot text length distribution
        plt.figure(figsize=(12, 6))
        sns.boxplot(data=self.df, x='document_type', y='text_length')
        plt.xticks(rotation=45)
        plt.title('Text Length Distribution by Document Type')
        plt.tight_layout()
        plt.show()
        
        # Create word cloud of titles
        text = ' '.join(self.df['title'].dropna())
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
        
        plt.figure(figsize=(15, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('Word Cloud of Document Titles')
        plt.show()
    
    def eurovoc_analysis(self):
        """Analyze eurovoc descriptors."""
        print("=== EuroVoc Descriptor Analysis ===")
        
        # Calculate descriptor frequencies
        all_descriptors = [desc for descs in self.df['eurovoc_descriptors'] for desc in descs]
        descriptor_freq = Counter(all_descriptors)
        
        print("\nMost common EuroVoc descriptors:")
        for desc, count in descriptor_freq.most_common(10):
            print(f"{desc}: {count}")
        
        # Calculate average number of descriptors per document
        self.df['descriptor_count'] = self.df['eurovoc_descriptors'].str.len()
        print("\nDescriptor count statistics:")
        print(self.df['descriptor_count'].describe())
        
        # Plot descriptor frequency distribution
        plt.figure(figsize=(15, 6))
        pd.Series(descriptor_freq).sort_values(ascending=False)[:20].plot(kind='bar')
        plt.title('Top 20 EuroVoc Descriptors')
        plt.xlabel('Descriptor')
        plt.ylabel('Frequency')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()
    
    def recommender_system_analysis(self):
        """Analyze aspects relevant for building a recommender system."""
        print("=== Recommender System Analysis ===")
        
        # Calculate descriptor co-occurrence matrix
        descriptor_pairs = []
        for descs in self.df['eurovoc_descriptors']:
            for i, desc1 in enumerate(descs):
                for desc2 in descs[i+1:]:
                    descriptor_pairs.append(tuple(sorted([desc1, desc2])))
        
        cooccurrence = Counter(descriptor_pairs)
        print("\nMost common descriptor pairs:")
        for pair, count in cooccurrence.most_common(10):
            print(f"{pair}: {count}")
        
        # Analyze temporal patterns
        self.df['year_month'] = self.df['date_document'].dt.to_period('M')
        temporal_patterns = self.df.groupby(['year_month', 'document_type']).size().unstack(fill_value=0)
        
        plt.figure(figsize=(15, 6))
        temporal_patterns.plot(kind='line')
        plt.title('Document Type Trends Over Time')
        plt.xlabel('Year-Month')
        plt.ylabel('Number of Documents')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.show()
        
        # Calculate document similarity distribution based on shared descriptors
        print("\nCalculating document similarity distribution...")
        sample_size = min(1000, len(self.df))  # Use a sample for large datasets
        sample_df = self.df.sample(sample_size)
        
        similarity_scores = []
        for i, row1 in enumerate(tqdm(sample_df.itertuples(), total=sample_size)):
            for row2 in sample_df.itertuples():
                if row1.Index < row2.Index:
                    common_descriptors = len(
                        set(row1.eurovoc_descriptors) & 
                        set(row2.eurovoc_descriptors)
                    )
                    if common_descriptors > 0:
                        similarity_scores.append(common_descriptors)
        
        plt.figure(figsize=(10, 6))
        plt.hist(similarity_scores, bins=20)
        plt.title('Distribution of Document Similarities\n(Based on Shared Descriptors)')
        plt.xlabel('Number of Shared Descriptors')
        plt.ylabel('Frequency')
        plt.tight_layout()
        plt.show()
    
    def run_complete_analysis(self):
        """Run all analyses in sequence."""
        print("Starting complete EURLex dataset analysis...")
        self.create_database()
        self.load_dataframe()
        self.basic_statistics()
        self.text_analysis()
        self.eurovoc_analysis()
        self.recommender_system_analysis()
        print("\nAnalysis complete!")

if __name__ == "__main__":
    eda = EURLexEDA()
    eda.run_complete_analysis()
