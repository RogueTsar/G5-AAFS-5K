from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
import logging

logger = logging.getLogger("finbert_tool")

# Global variables to cache model and tokenizer
_tokenizer = None
_model = None
_nlp_pipeline = None

def get_finbert_pipeline():
    """Lazily load the FinBERT model and tokenizer."""
    global _tokenizer, _model, _nlp_pipeline
    if _nlp_pipeline is None:
        try:
            from transformers import logging as transformers_logging
            # Suppress specific transformers warnings during loading
            # This handles the harmless bert.embeddings.position_ids UNEXPECTED warning
            transformers_logging.set_verbosity_error()
            
            model_name = "ProsusAI/finbert"
            logger.info(f"Loading FinBERT model: {model_name}")
            _tokenizer = AutoTokenizer.from_pretrained(model_name)
            _model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # Reset verbosity back to info/warning if needed, or keep it suppressed for the pipeline creation
            transformers_logging.set_verbosity_warning()
            
            _nlp_pipeline = pipeline("sentiment-analysis", model=_model, tokenizer=_tokenizer, truncation=True, max_length=512)
        except Exception as e:
            logger.error(f"Error loading FinBERT model: {str(e)}")
            return None
    return _nlp_pipeline

def analyze_financial_sentiment(text: str) -> dict:
    """
    Analyzes the sentiment of financial text using FinBERT.
    
    Args:
        text (str): The financial text to analyze.
        
    Returns:
        dict: A dictionary containing 'label' (positive, negative, neutral) and 'score'.
    """
    nlp = get_finbert_pipeline()
    if not nlp:
        return {"error": "Could not initialize FinBERT pipeline"}

    try:
        # FinBERT has a max length of 512 tokens
        result = nlp(text[:2000])[0] # Truncate characters as a safety measure, pipeline handles tokens
        return {
            "label": result["label"],
            "score": result["score"]
        }
    except Exception as e:
        logger.error(f"Error during FinBERT analysis: {str(e)}")
        return {"error": str(e)}

def analyze_multiple_sentences(sentences: list) -> list:
    """
    Analyzes multiple financial sentences and returns a list of results.
    """
    nlp = get_finbert_pipeline()
    if not nlp:
        return [{"error": "Could not initialize FinBERT pipeline"}] * len(sentences)

    results = []
    for sentence in sentences:
        results.append(analyze_financial_sentiment(sentence))
    return results
