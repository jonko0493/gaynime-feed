from sklearn.base import TransformerMixin

def clean_text(text):
    return text.strip().lower()

class predictors(TransformerMixin):
    def transform(self, X, **transform_params):
        # Implement clean_text
        return [clean_text(text) for text in X]
    def fit(self, X, y=None, **fit_params):
        return self
    def get_params(self, deep=True):
        return {}