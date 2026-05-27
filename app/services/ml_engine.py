from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sqlalchemy.orm import Session
from ..models import Transaction, Category
import pandas as pd

class CategorizationEngine:
    def __init__(self, db: Session):
        self.db = db
        self.vectorizer = CountVectorizer()
        self.clf = MultinomialNB()
        self.is_trained = False

    def train(self):
        # Fetch transactions that have categories
        data = self.db.query(Transaction, Category).join(Category).all()
        if not data:
            return

        descriptions = [t.Transaction.description for t in data]
        labels = [t.Category.name for t in data]

        X = self.vectorizer.fit_transform(descriptions)
        self.clf.fit(X, labels)
        self.is_trained = True

    def predict(self, description: str):
        if not self.is_trained:
            return None
        
        X = self.vectorizer.transform([description])
        return self.clf.predict(X)[0]

def auto_categorize_transactions(db: Session):
    engine = CategorizationEngine(db)
    engine.train()
    
    # Predict for uncategorized transactions
    uncategorized = db.query(Transaction).filter(Transaction.category_id == None).all()
    for t in uncategorized:
        prediction = engine.predict(t.description)
        if prediction:
            category = db.query(Category).filter(Category.name == prediction).first()
            if category:
                t.category_id = category.id
    
    db.commit()
